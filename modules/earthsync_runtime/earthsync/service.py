"""EarthSync service facade: the interface other ORBITILL agents consume.

Contract functions (snake_case here; camelCase aliases at the bottom):
  get_environmental_series  (getEnvironmentalSeries)
  get_source_metadata       (getSourceMetadata)
  get_data_availability     (getDataAvailability)
  compare_climate_datasets  (compareClimateDatasets)
  get_evidence_for_calculation (getEvidenceForCalculation)
  build_evidencefusion_report

Every call returns a ``ServiceResult`` envelope: status ok | partial | insufficient, plus typed insufficiencies.
Resolution order for POWER data: cache/live -> real bundled fixture -> synthetic fixture (ONLY if allowed).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from . import chain as CH
from . import features as F
from .access_policy import AccessPolicy
from .adapters import nasa_power as NP
from .cache import ResponseCache
from .compare import DatasetComparison, compare_series
from .errors import EarthSyncError
from .fixtures import find_fixture, list_fixtures
from .manifest import ORGANIZER_NAME, get_source, load_manifest
from .schemas import (EnvironmentalSeries, EvidenceRecord, Insufficiency, InsufficiencyCode, clean_floats)

COUNTRY_KEY = {"BD": "BD", "US": "US"}


class ServiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    schema_version: str = "1.0.0"
    status: Literal["ok", "partial", "insufficient"]
    data: dict[str, Any] = Field(default_factory=dict)
    insufficiency: list[Insufficiency] = Field(default_factory=list)
    warnings: list[Insufficiency] = Field(default_factory=list)
    retrieval: dict[str, Any] = Field(default_factory=dict)
    is_synthetic: bool = False
    banner: Optional[str] = None


SYNTH_BANNER = "SYNTHETIC DEMONSTRATION DATA - not a NASA retrieval. Do not present as measurements."


def slice_series(s: EnvironmentalSeries, start: str, end: str) -> EnvironmentalSeries:
    idx = [i for i, d in enumerate(s.dates) if start <= d <= end]
    ds = [s.dates[i] for i in idx]
    return s.model_copy(update={"dates": ds, "values": [s.values[i] for i in idx], "flags": {d: s.flags[d] for d in ds if d in s.flags},
                                "temporal": s.temporal.model_copy(update={"start": ds[0] if ds else None, "end": ds[-1] if ds else None})})


class EarthSync:
    def __init__(self, policy: Optional[AccessPolicy] = None, transport: Optional[NP.Transport] = None, fixture_root: Optional[Path] = None):
        self.policy = policy or AccessPolicy()
        self.client = NP.PowerClient(self.policy, transport)
        self.fixture_root = fixture_root
        self.store: dict[str, Any] = {"evidence": {}, "series": {}, "features": {}, "chains": {}, "comparisons": {}}

    # ------------------------------------------------------------ series
    def get_environmental_series(self, lat: float, lon: float, start: str, end: str, variables: Sequence[str] = NP.DEFAULT_PARAMS, *,
                                 community: str = "AG", allow_fixture: Optional[bool] = None, force_refresh: bool = False) -> ServiceResult:
        allow_syn = self.policy.allow_synthetic_fixture if allow_fixture is None else allow_fixture
        try:
            req = NP.PowerRequest(lat, lon, date.fromisoformat(start), date.fromisoformat(end), tuple(variables), community)
            req.validate()
        except ValueError as e:
            return ServiceResult(status="insufficient", insufficiency=[Insufficiency(code=InsufficiencyCode.parameter_rejected, message=f"Invalid request: {e}")])
        notes: list[Insufficiency] = []
        parsed = None
        try:
            got = self.client.fetch(req, force_refresh=force_refresh)
            parsed = NP.parse_power_payload(got.payload, req, url=got.url, retrieved_at_utc=got.retrieved_at_utc, mode=got.mode, payload_sha256=got.payload_sha256)
        except EarthSyncError as e:
            notes.append(e.insufficiency)
            try:
                hit = find_fixture(req, allow_synthetic=allow_syn, root=self.fixture_root)
                syn = hit.kind == "synthetic_demo"
                full = NP.PowerRequest(req.lat, req.lon, date.fromisoformat(hit.meta["request"]["start"]), date.fromisoformat(hit.meta["request"]["end"]),
                                       tuple(hit.meta["request"]["parameters"]), hit.meta["request"].get("community", "AG"))
                parsed = NP.parse_power_payload(hit.fetch.payload, full, url=hit.fetch.url, retrieved_at_utc=hit.fetch.retrieved_at_utc, mode=hit.fetch.mode,
                                                payload_sha256=hit.fetch.payload_sha256, is_synthetic=syn)
                notes.append(Insufficiency(code=InsufficiencyCode.source_unavailable, severity="degrading",
                                           message=f"Live/cache unavailable; served bundled {'SYNTHETIC demonstration' if syn else 'real'} fixture {hit.path.name}"))
            except EarthSyncError as e2:
                notes.append(e2.insufficiency)
                return ServiceResult(status="insufficient", insufficiency=notes)
        out = {}
        for k, s in parsed.series.items():
            if k in variables:
                sl = slice_series(s, start, end)
                out[k] = sl
                self.store["series"][sl.series_id] = sl
        self.store["evidence"][parsed.evidence.evidence_id] = parsed.evidence
        missing = [v for v in variables if v not in out]
        warns = list(parsed.warnings) + notes
        syn = parsed.evidence.is_synthetic
        status = "ok" if not missing else ("partial" if out else "insufficient")
        for m in missing:
            warns.append(F.missing_variable(m, "getEnvironmentalSeries"))
        return ServiceResult(status=status, data={"series": {k: v.model_dump(mode="json") for k, v in out.items()}, "evidence": parsed.evidence.model_dump(mode="json")},
                             warnings=warns, retrieval={"mode": parsed.evidence.retrieval_mode, "retrieved_at_utc": parsed.evidence.retrieved_at_utc, "url": parsed.evidence.original_url},
                             is_synthetic=syn, banner=SYNTH_BANNER if syn else None)

    def series_objects(self, res: ServiceResult) -> dict[str, EnvironmentalSeries]:
        return {k: EnvironmentalSeries.model_validate(v) for k, v in res.data.get("series", {}).items()}

    # ---------------------------------------------------------- metadata
    def get_source_metadata(self, source_id: str) -> dict:
        return get_source(source_id).model_dump(mode="json")

    def list_sources(self, organizer_only: bool = False) -> list[dict]:
        return [e.model_dump(mode="json") for e in load_manifest().values() if (e.organizer_listed or not organizer_only)]

    # ------------------------------------------------------ availability
    def get_data_availability(self, country_iso: str, lat: float, lon: float, start: Optional[str] = None, end: Optional[str] = None) -> dict:
        """What can EarthSync deliver for this place right now? ``country_iso`` is supplied by the caller (RegionProfile);
        we do not guess countries from coordinates (a bounding box would mislabel e.g. Kolkata as Bangladesh)."""
        ckey = COUNTRY_KEY.get(country_iso.upper(), "GLOBAL")
        req = NP.PowerRequest(lat, lon, date(1991, 1, 1), date(1991, 1, 2))
        met, sol = req.cells()
        cached = []
        for e in ResponseCache(self.policy.cache_dir).list_entries():
            r = (e.get("meta") or {}).get("request")
            if r and r["met_cell"] == met.cell_id and r["solar_cell"] == sol.cell_id:
                cached.append({"start": r["start"], "end": r["end"], "retrieved_at_utc": e["retrieved_at_utc"], "parameters": r["parameters"]})
        fx = []
        for path, doc in list_fixtures(self.fixture_root):
            m = doc.get("_fixture", {})
            r = m.get("request", {})
            try:
                fr = NP.PowerRequest(r["lat"], r["lon"], date.fromisoformat(r["start"]), date.fromisoformat(r["end"]), tuple(r["parameters"]))
            except Exception:
                continue
            if fr.cells()[0].cell_id == met.cell_id and fr.cells()[1].cell_id == sol.cell_id:
                fx.append({"file": path.name, "kind": m.get("kind"), "start": r["start"], "end": r["end"],
                           "retrieved_at_utc": (m.get("fetch") or {}).get("retrieved_at_utc"), "parameters": r["parameters"]})
        rows = []
        for e in load_manifest().values():
            app = e.applicability.get(ckey, "not_applicable")
            pri = {"BD": e.priority_bd, "US": e.priority_us}.get(ckey, e.priority_global)
            if app == "not_applicable":
                access, why = "not_applicable_for_region", f"{e.name} does not apply to {country_iso} (see manifest caveat)."
            elif e.source_id == "NASA_POWER":
                if cached:
                    access, why = "available_via_cache", "Cached live response(s) exist for this grid cell."
                elif any(f["kind"] == "real_retrieval" for f in fx):
                    access, why = "available_real_fixture", "Real bundled fixture covers this grid cell."
                elif fx:
                    access, why = "synthetic_fixture_only_live_needs_network", "Only SYNTHETIC demo data is bundled; live fetch needs network access to power.larc.nasa.gov."
                else:
                    access, why = "live_fetch_needed", "No cache or fixture for this grid cell; live fetch needs network access."
            elif any(n.startswith("Owned by") for n in e.notes):
                access, why = "owned_by_other_agent", next(n for n in e.notes if n.startswith("Owned by")) + " EarthSync only registers it in the manifest."
            elif e.live_decision == "live_designed_untested":
                access, why = "designed_untested", "Request path designed; parameter/response not verified."
            elif e.live_decision == "offline_extract_ingest":
                access, why = "extract_ingest_only", "Supply a user-downloaded extract with declared metadata."
            elif e.live_decision in ("methodology_reference",):
                access, why = "methodology_only", "Method reference; implemented where noted."
            elif e.auth_required in ("earthdata_login", "api_key", "registration"):
                access, why = "requires_credentials_and_adapter", "Adapter not implemented and credentials needed; downstream receives adapter_not_implemented."
            else:
                access, why = "not_implemented", "No adapter in EarthSync; downstream receives adapter_not_implemented."
            rows.append({"source_id": e.source_id, "name": e.name, "organizer_listed": e.organizer_listed, "applicability": app, "priority": pri, "access_now": access,
                         "reason": why, "native_spatial": e.native_spatial, "native_temporal": e.native_temporal, "latency": e.latency, "live_decision": e.live_decision,
                         "license": e.license.name, "license_verified": e.license.verified, "critical_caveat": e.critical_caveat})
        order = {"P0": 0, "P1": 1, "P1_STRETCH": 2, "P2": 3, "P2_US": 3, "P3": 4, "N/A": 9}
        rows.sort(key=lambda r: (order.get(r["priority"], 8), r["source_id"]))
        return {"schema_version": "1.0.0", "country_iso": country_iso.upper(), "lat": lat, "lon": lon,
                "grid_cells": {"power_meteorology": met.cell_id, "power_solar": sol.cell_id},
                "power_cached": cached, "power_fixtures": fx,
                "ready": {"power_daily": bool(cached or fx), "power_daily_real": bool(cached or any(f["kind"] == "real_retrieval" for f in fx)),
                          "rain_crosscheck": False, "vegetation_ndvi": False, "soil_moisture": False,
                          "note": "Cross-check/vegetation/soil-moisture flags stay False until an extract is ingested; EarthSync never fabricates them."},
                "sources": rows}

    # ----------------------------------------------------------- compare
    def compare_climate_datasets(self, a: Optional[EnvironmentalSeries], b: Optional[EnvironmentalSeries], **kw) -> DatasetComparison:
        c = compare_series(a, b, **kw)
        self.store["comparisons"][c.comparison_id] = c
        return c

    # ----------------------------------------------------------- chains
    def build_chain(self, *, title: str, question: str, feature: F.Feature, rule: CH.ConstraintRule, series: list[EnvironmentalSeries],
                    extra_series: Optional[list[EnvironmentalSeries]] = None) -> CH.EvidenceChain:
        for s in list(series) + list(extra_series or []):
            self.store["series"][s.series_id] = s
        ch = CH.build_chain(title=title, question=question, feature=feature, rule=rule, series=series, evidence=self.store["evidence"], extra_series=extra_series)
        self.store["features"][feature.feature_id] = feature
        self.store["chains"][ch.chain_id] = ch
        self.store["chains"][ch.evaluation.evaluation_id] = ch
        return ch

    def register_derived(self, series: EnvironmentalSeries, ev: EvidenceRecord) -> None:
        self.store["series"][series.series_id] = series
        self.store["evidence"][ev.evidence_id] = ev

    def get_evidence_for_calculation(self, calc_id: str) -> ServiceResult:
        """Resolve a chain/evaluation/feature id to its full lineage: graph + evidence records + license list."""
        ch = self.store["chains"].get(calc_id)
        feat = self.store["features"].get(calc_id)
        if ch is None and feat is not None:
            ch = next((c for c in self.store["chains"].values() if any(f.feature_id == calc_id for f in c.features)), None)
        if ch is None:
            return ServiceResult(status="insufficient", insufficiency=[Insufficiency(code=InsufficiencyCode.missing_variable, message=f"No calculation registered under id {calc_id!r}",
                                                                                    remedy="Build the chain first (service.build_chain) in this process.")])
        ev_ids = set()
        for n in ch.graph.nodes:
            if n.kind == "source":
                ev_ids.add(n.detail["evidence_id"])
        recs = [self.store["evidence"][i].model_dump(mode="json") for i in sorted(ev_ids) if i in self.store["evidence"]]
        problems = CH.validate_graph(ch.graph)
        return ServiceResult(status="ok" if not problems else "partial", data={"chain": ch.model_dump(mode="json"), "evidence_records": recs, "graph_problems": problems,
                                                                               "mermaid": CH.graph_to_mermaid(ch.graph)},
                             is_synthetic=ch.is_synthetic, banner=ch.banner)

    # ------------------------------------------------------- demo chains
    DEMO_RULES = {
        "monsoon_dry_spell": CH.ConstraintRule(
            rule_id="DEMO_dry_spell_ge_10d", description="Dry spell (rain < 1 mm/day) of 10+ days during the window", violation_if=">=", threshold=10.0, unit="days",
            owner="SoilBrain", rule_source="DEMO - illustrative threshold; SoilBrain/AquaSense must supply a cited crop-stage rule", is_demo=True,
            applies_to="rainfed establishment risk (illustrative)", consequence_if_violated="Rainfall alone may not sustain the crop through this window; irrigation need should be checked by the water module."),
        "terminal_heat_days": CH.ConstraintRule(
            rule_id="DEMO_heat_days_ge_5", description="5+ days with Tmax >= 32 degC in the window", violation_if=">=", threshold=5.0, unit="days",
            owner="SoilBrain", rule_source="DEMO - illustrative threshold; SoilBrain must supply a cited wheat grain-filling heat rule for Bangladesh", is_demo=True,
            applies_to="cool-season cereal grain filling (illustrative)", consequence_if_violated="Heat during grain filling can reduce yield; the crop-rule owner decides how this affects rotation feasibility."),
    }

    def demo_chains(self, series: dict[str, EnvironmentalSeries], year: int, *, md_dryspell=("06-01", "09-30"), md_heat=("02-15", "03-15")) -> list[CH.EvidenceChain]:
        out = []
        r = series.get("PRECTOTCORR")
        f1 = F.longest_spell(r, f"{year}-{md_dryspell[0]}", f"{year}-{md_dryspell[1]}", below=1.0, name="Longest dry spell (rain < 1 mm/day)")
        out.append(self.build_chain(title="Monsoon-season dry-spell evidence", question="Did rainfall leave long dry gaps in this season window?", feature=f1,
                                    rule=self.DEMO_RULES["monsoon_dry_spell"], series=[r] if r else []))
        t = series.get("T2M_MAX")
        f2 = F.count_days(t, f"{year}-{md_heat[0]}", f"{year}-{md_heat[1]}", op=">=", threshold=32.0, name="Days with Tmax >= 32 degC")
        out.append(self.build_chain(title="Cool-season heat-day evidence", question="How many hot days fell in the grain-filling window?", feature=f2,
                                    rule=self.DEMO_RULES["terminal_heat_days"], series=[t] if t else []))
        return out


# camelCase aliases requested by the shared contract
EarthSync.getEnvironmentalSeries = EarthSync.get_environmental_series
EarthSync.getSourceMetadata = EarthSync.get_source_metadata
EarthSync.getDataAvailability = EarthSync.get_data_availability
EarthSync.compareClimateDatasets = EarthSync.compare_climate_datasets
EarthSync.getEvidenceForCalculation = EarthSync.get_evidence_for_calculation
_ = (datetime, timezone, ORGANIZER_NAME, clean_floats)
