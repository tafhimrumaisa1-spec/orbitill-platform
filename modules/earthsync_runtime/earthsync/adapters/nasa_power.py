"""NASA POWER daily point adapter (P0).

Official endpoint (docs verified in-session via power.larc.nasa.gov docs pages):
    GET https://power.larc.nasa.gov/api/temporal/daily/point
        ?parameters=T2M,PRECTOTCORR,...&community=AG&longitude=..&latitude=..
        &start=YYYYMMDD&end=YYYYMMDD&format=JSON
No authentication; data licensed CC BY 4.0. Guidance from the tutorial: at most 5
concurrent requests, request no finer than native resolution (0.5x0.625 deg
meteorology, 1x1 deg solar), do not repeatedly request the same location.

What this adapter guarantees
----------------------------
* Units come from the *response* ``parameters`` metadata and are converted to
  canonical units (e.g. kW-hr/m^2/day -> MJ/m^2/day); unknown unit -> typed failure.
* Fill value (header ``fill_value``, normally -999) -> ``None`` + ``fill_value`` flag.
* Plausibility bounds per variable; out-of-range -> ``None`` + ``rejected_out_of_range``.
* The most recent days are flagged ``nrt_provisional`` (POWER latency 2-7 days and
  recent values are revised).
* Responses are cached by (met cell, solar cell, dates, params, community, time standard)
  so farms in the same grid cell share one request.
* Typed failures; never a guessed value.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, NamedTuple, Optional, Protocol
from urllib.parse import urlencode

from .. import gridinfo as G
from ..access_policy import USER_AGENT, AccessPolicy, redact_secrets
from ..cache import ResponseCache, canonical_json, key_hash, sha256_text, utcnow_iso
from ..errors import OfflineCacheMiss, SourceError
from ..schemas import (EnvironmentalSeries, EvidenceRecord, Insufficiency, InsufficiencyCode, LicenseInfo,
                       SpatialSupport, TemporalSupport, TransformationStep)
from ..units import CANON, UnitError, to_canonical
from ..variables import POWER_VARS, VarSpec

ADAPTER_VERSION = "earthsync-power/0.1.0"
BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
SOURCE_ID = "NASA_POWER"
POWER_START = date(1981, 1, 1)
MAX_PARAMS = 20  # per official daily API page
MAX_SPAN_YEARS = 45
NRT_PROVISIONAL_DAYS = 7  # POWER latency "2 to 7 days" (official llms.txt)

DEFAULT_PARAMS = ("T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M", "PS")

LICENSE = LicenseInfo(
    name="CC BY 4.0",
    url="https://power.larc.nasa.gov/docs/referencing/",
    attribution="These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the "
                "NASA Earth Science/Applied Science Program.",
    verified=True,
    note="License and operator confirmed from https://power.larc.nasa.gov/llms.txt during this build. Attribution wording: "
         "confirm the current text at the referencing page before publication.",
)
CITATION = ("NASA POWER Project, NASA Langley Research Center. Prediction Of Worldwide Energy Resources (POWER) "
            "Daily API. https://power.larc.nasa.gov/")


# ------------------------------------------------------------------ transport
class TransportResponse(NamedTuple):
    status: int
    body: str
    headers: dict
    url: str


class Transport(Protocol):
    def get(self, url: str, params: dict, timeout: float) -> TransportResponse: ...


class RequestsTransport:
    """Default transport (requests). Honors REQUESTS_CA_BUNDLE / HTTPS_PROXY from the environment."""

    def __init__(self) -> None:
        import requests

        self._requests = requests
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

    def get(self, url: str, params: dict, timeout: float) -> TransportResponse:
        r = self._session.get(url, params=params, timeout=timeout)
        return TransportResponse(r.status_code, r.text, dict(r.headers), r.url)


# -------------------------------------------------------------------- request
@dataclass(frozen=True)
class PowerRequest:
    lat: float
    lon: float
    start: date
    end: date
    parameters: tuple[str, ...] = DEFAULT_PARAMS
    community: str = "AG"
    time_standard: Optional[str] = None  # None => provider default (recorded as such)

    def validate(self, today: Optional[date] = None) -> None:
        today = today or datetime.now(timezone.utc).date()
        if not -90 <= self.lat <= 90 or not -180 <= self.lon <= 180:
            raise ValueError("lat/lon out of range")
        if self.start < POWER_START:
            raise ValueError(f"POWER daily data start {POWER_START}; got {self.start}")
        if self.end < self.start:
            raise ValueError("end before start")
        if self.end > today:
            raise ValueError(f"end {self.end} is in the future (today {today}); POWER holds no forecasts")
        if (self.end - self.start).days > 366 * MAX_SPAN_YEARS:
            raise ValueError("date span too large; split the request")
        if not 1 <= len(self.parameters) <= MAX_PARAMS:
            raise ValueError(f"1..{MAX_PARAMS} parameters per request")
        for p in self.parameters:
            if not p.replace("_", "").isalnum() or p != p.upper():
                raise ValueError(f"suspicious parameter name {p!r}")
        if self.community.upper() not in ("AG", "RE", "SB"):
            raise ValueError("community must be AG, RE or SB")
        if self.time_standard not in (None, "UTC", "LST"):
            raise ValueError("time_standard must be None, 'UTC' or 'LST'")

    def query(self) -> dict:
        q = {
            "parameters": ",".join(self.parameters),
            "community": self.community.upper(),
            "longitude": f"{self.lon:.4f}",
            "latitude": f"{self.lat:.4f}",
            "start": self.start.strftime("%Y%m%d"),
            "end": self.end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        if self.time_standard:
            q["time-standard"] = self.time_standard
        return q

    def url(self) -> str:
        return f"{BASE_URL}?{urlencode(self.query(), safe=',')}"

    def cells(self) -> tuple[G.Cell, G.Cell]:
        return G.cell_for(self.lat, self.lon, G.MERRA2), G.cell_for(self.lat, self.lon, G.CERES_1DEG)

    def cache_key(self) -> str:
        met, sol = self.cells()
        return key_hash({
            "ep": "power/daily/point", "met": met.cell_id, "solar": sol.cell_id,
            "start": self.start.isoformat(), "end": self.end.isoformat(),
            "params": sorted(self.parameters), "community": self.community.upper(),
            "ts": self.time_standard or "provider_default",
        })


# ------------------------------------------------------------------- results
@dataclass
class PowerFetch:
    payload: dict
    url: str
    retrieved_at_utc: str
    mode: str  # live_fetch | cache_hit | stale_cache
    payload_sha256: str
    cache_age_days: float = 0.0


@dataclass
class PowerParsed:
    series: dict[str, EnvironmentalSeries]
    evidence: EvidenceRecord
    warnings: list[Insufficiency]


def _classify_http(status: int, body: str) -> Insufficiency:
    snippet = redact_secrets(body[:300].replace("\n", " "))
    if status in (400, 422):
        return Insufficiency(code=InsufficiencyCode.parameter_rejected,
                             message=f"POWER rejected the request (HTTP {status}): {snippet}",
                             remedy="Check parameter names for this community and the date range.")
    if status == 429:
        return Insufficiency(code=InsufficiencyCode.source_unavailable, message="POWER rate-limited the client (HTTP 429)",
                             remedy="Reduce concurrency (max 5) and rely on the cache.")
    return Insufficiency(code=InsufficiencyCode.source_unavailable, message=f"POWER HTTP {status}: {snippet}",
                         remedy="Retry later; use cached/offline data meanwhile.")


class PowerClient:
    def __init__(self, policy: Optional[AccessPolicy] = None, transport: Optional[Transport] = None,
                 sleeper: Callable[[float], None] = time.sleep, now: Optional[Callable[[], datetime]] = None):
        self.policy = policy or AccessPolicy()
        self.transport = transport
        self.cache = ResponseCache(self.policy.cache_dir)
        self._sleep = sleeper
        self._now = now or (lambda: datetime.now(timezone.utc))

    # ---- TTL: recent data is revised, history is stable
    def _ttl_days(self, req: PowerRequest) -> float:
        recent = (self._now().date() - req.end).days < 30
        return self.policy.recent_data_ttl_days if recent else self.policy.historical_ttl_days

    def fetch(self, req: PowerRequest, *, force_refresh: bool = False) -> PowerFetch:
        req.validate(self._now().date())
        key = req.cache_key()
        entry = self.cache.get(key)
        if entry and not force_refresh and self.cache.age_days(entry, self._now()) <= self._ttl_days(req):
            return PowerFetch(entry["payload"], entry["url"], entry["retrieved_at_utc"], "cache_hit",
                              entry["payload_sha256"], self.cache.age_days(entry, self._now()))
        if self.policy.offline:
            if entry:
                return PowerFetch(entry["payload"], entry["url"], entry["retrieved_at_utc"], "stale_cache",
                                  entry["payload_sha256"], self.cache.age_days(entry, self._now()))
            raise OfflineCacheMiss(Insufficiency(
                code=InsufficiencyCode.offline_cache_miss,
                message="Offline mode and no cached POWER response for this request.",
                remedy="Run `earthsync fetch-power` on a networked machine, or ship an offline bundle."))
        try:
            payload, url = self._get_live(req)
        except SourceError as e:
            if entry:  # degrade to stale cache, visibly
                return PowerFetch(entry["payload"], entry["url"], entry["retrieved_at_utc"], "stale_cache",
                                  entry["payload_sha256"], self.cache.age_days(entry, self._now()))
            raise e
        retrieved = self._now().strftime("%Y-%m-%dT%H:%M:%SZ")
        saved = self.cache.put(key, url=url, payload=payload, retrieved_at_utc=retrieved,
                               meta={"adapter": ADAPTER_VERSION, "request": {
                                   "met_cell": req.cells()[0].cell_id, "solar_cell": req.cells()[1].cell_id,
                                   "start": req.start.isoformat(), "end": req.end.isoformat(),
                                   "parameters": list(req.parameters), "community": req.community.upper()}})
        return PowerFetch(payload, url, retrieved, "live_fetch", saved["payload_sha256"], 0.0)

    # ---- live GET with bounded retries; every failure typed
    def _get_live(self, req: PowerRequest) -> tuple[dict, str]:
        if self.transport is None:
            self.transport = RequestsTransport()
        q = req.query()
        last: Optional[Insufficiency] = None
        for attempt in range(1, self.policy.max_retries + 1):
            self.policy.acquire()
            try:
                resp = self.transport.get(BASE_URL, q, self.policy.timeout_s)
            except Exception as exc:  # network layer: classify, never leak secrets
                text = redact_secrets(f"{type(exc).__name__}: {exc}")
                blocked = "Tunnel connection failed" in text or "403 Forbidden" in text or "ProxyError" in text
                last = Insufficiency(
                    code=InsufficiencyCode.egress_blocked if blocked else InsufficiencyCode.source_unavailable,
                    message=("Outbound network policy refused the connection to power.larc.nasa.gov" if blocked
                             else f"Network error contacting POWER: {text[:200]}"),
                    remedy="Allow power.larc.nasa.gov in the network policy, or use cached/offline fixtures.")
                if blocked:
                    break  # a policy refusal is not retried
            else:
                if resp.status == 200:
                    try:
                        return json.loads(resp.body), redact_secrets(resp.url or req.url())
                    except json.JSONDecodeError:
                        last = Insufficiency(code=InsufficiencyCode.invalid_response,
                                             message="POWER returned HTTP 200 with a non-JSON body")
                else:
                    last = _classify_http(resp.status, resp.body)
                    if resp.status in (400, 422):
                        break  # our request is wrong; retrying cannot help
            finally:
                self.policy.release()
            if attempt < self.policy.max_retries:
                self._sleep(min(2 ** attempt, 30))
        assert last is not None
        raise SourceError(last)


# ------------------------------------------------------------------- parsing
def parse_power_payload(payload: dict, req: PowerRequest, *, url: str, retrieved_at_utc: str, mode: str,
                        payload_sha256: str, is_synthetic: bool = False,
                        now: Optional[datetime] = None) -> PowerParsed:
    """Convert a POWER JSON payload into harmonised EnvironmentalSeries + one EvidenceRecord."""
    try:
        params_block = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise SourceError(Insufficiency(code=InsufficiencyCode.invalid_response,
                                        message="POWER payload lacks properties.parameter")) from exc
    header = payload.get("header", {}) or {}
    meta = payload.get("parameters", {}) or {}
    fill = float(header.get("fill_value", -999.0))
    geom = (payload.get("geometry") or {}).get("coordinates") or []
    api_version = ((header.get("api") or {}).get("version")) or None
    now = now or datetime.now(timezone.utc)
    ref_day = datetime.strptime(retrieved_at_utc, "%Y-%m-%dT%H:%M:%SZ").date() if retrieved_at_utc else now.date()
    nrt_cut = (ref_day - timedelta(days=NRT_PROVISIONAL_DAYS)).isoformat()

    met_cell, sol_cell = req.cells()
    evidence_id = f"ev:power:{payload_sha256[:12]}"
    ingestion = utcnow_iso()
    series: dict[str, EnvironmentalSeries] = {}
    warnings: list[Insufficiency] = []
    ts = req.time_standard or "provider_default"
    day_note = ("Provider-default day boundary (not set explicitly). Bangladesh is UTC+6: if the provider day is UTC, "
                "daily values are offset ~6 h from the local civil day; seasonal totals are unaffected, day-by-day "
                "comparisons with IMERG/gauges can shift by one day." if ts == "provider_default" else f"time-standard={ts}")
    transform_steps = [
        TransformationStep(step_id="t1", name="fill_value_to_missing", params={"fill_value": fill},
                           description="Provider fill values become None with flag fill_value."),
        TransformationStep(step_id="t2", name="unit_normalisation", params={"source": "response.parameters[*].units"},
                           description="Units read from the response and converted to canonical units."),
        TransformationStep(step_id="t3", name="plausibility_bounds", description="Out-of-range values -> None + rejected_out_of_range."),
    ]
    if is_synthetic:
        transform_steps.insert(0, TransformationStep(step_id="t0", name="SYNTHETIC_GENERATION",
                                                     description="Demonstration data generated by scripts/make_synthetic_fixture.py. NOT a NASA retrieval."))

    for pname in req.parameters:
        spec: Optional[VarSpec] = POWER_VARS.get(pname)
        raw = params_block.get(pname)
        if raw is None:
            warnings.append(Insufficiency(code=InsufficiencyCode.missing_variable,
                                          message=f"POWER response did not include {pname}", missing=[pname], severity="degrading"))
            continue
        if spec is None:
            warnings.append(Insufficiency(code=InsufficiencyCode.adapter_not_implemented,
                                          message=f"No unit/QC spec registered for {pname}; skipped (not guessed)",
                                          missing=[pname], severity="degrading"))
            continue
        src_unit = (meta.get(pname) or {}).get("units")
        if not src_unit:
            warnings.append(Insufficiency(code=InsufficiencyCode.unit_unrecognized,
                                          message=f"No unit metadata for {pname} in response; refusing to assume",
                                          missing=[pname], severity="degrading"))
            continue
        dates = sorted(raw.keys())
        vals: list[Optional[float]] = []
        flags: dict[str, list[str]] = {}
        converted_any = False
        try:
            for d in dates:
                v = raw[d]
                iso = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                f: list[str] = []
                if v is None or float(v) == fill or float(v) <= -990:
                    vals.append(None)
                    flags[iso] = ["fill_value"]
                    continue
                cv, canon, conv = to_canonical(float(v), src_unit, spec.dimension)
                converted_any = converted_any or conv
                if conv:
                    f.append("unit_converted")
                if not (spec.lo <= cv <= spec.hi):
                    vals.append(None)
                    flags[iso] = ["rejected_out_of_range"]
                    continue
                if iso >= nrt_cut:
                    f.append("nrt_provisional")
                if is_synthetic:
                    f.append("synthetic")
                vals.append(round(cv, 4))
                if f:
                    flags[iso] = f
        except UnitError as ue:
            warnings.append(ue.to_insufficiency())
            continue
        iso_dates = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in dates]
        grid_spec = spec.grid
        spatial = G.spatial_support_for(req.lat, req.lon, grid_spec)
        sid = f"ser:power:{pname}:{spatial.cell_id}:{iso_dates[0]}..{iso_dates[-1]}:{payload_sha256[:8]}"
        series[pname] = EnvironmentalSeries(
            series_id=sid, source_id=SOURCE_ID, source_version=api_version, variable=spec.variable,
            provider_variable=pname, unit=CANON[spec.dimension], dates=iso_dates, values=vals, flags=flags,
            spatial=spatial,
            temporal=TemporalSupport(step="daily", time_standard=ts if ts != "provider_default" else "provider_default",
                                     start=iso_dates[0], end=iso_dates[-1],
                                     latency_note="POWER latency 2-7 days; most recent days flagged nrt_provisional",
                                     day_boundary_note=day_note),
            data_type="hypothetical_scenario" if is_synthetic else "model_estimate",
            measurement_process="synthetic_demo" if is_synthetic else spec.process,
            evidence_id=evidence_id, retrieval_mode=_mode_to_series_mode(mode, is_synthetic), ingestion_time=ingestion,
            is_synthetic=is_synthetic,
            caveats=([spec.note] if spec.note else []) + (["SYNTHETIC DEMONSTRATION DATA - not a NASA retrieval"] if is_synthetic else []),
        )

    met_support = G.spatial_support_for(req.lat, req.lon, G.MERRA2)
    evidence = EvidenceRecord(
        evidence_id=evidence_id, source_id=SOURCE_ID,
        provider=("SYNTHETIC - generated by EarthSync (NOT NASA)" if is_synthetic else "NASA Langley Research Center - POWER Project"),
        dataset_name=header.get("title") or "NASA POWER daily point data",
        dataset_version=api_version, original_url=redact_secrets(url), citation=("None - synthetic data cannot be cited as NASA data" if is_synthetic else CITATION),
        retrieved_at_utc=retrieved_at_utc, retrieval_mode=_mode_to_series_mode(mode, is_synthetic),
        spatial=met_support,
        temporal=TemporalSupport(step="daily", time_standard=ts if ts != "provider_default" else "provider_default",
                                 start=req.start.isoformat(), end=req.end.isoformat(),
                                 latency_note="2-7 days (official POWER overview)", day_boundary_note=day_note),
        variables=sorted(series.keys()), transformations=transform_steps,
        license=(LicenseInfo(name="n/a - synthetic demonstration data", verified=True, note="Generated by scripts/make_synthetic_fixture.py") if is_synthetic else LICENSE),
        payload_sha256=payload_sha256, adapter_version=ADAPTER_VERSION, is_synthetic=is_synthetic,
        caveats=[
            "Gridded meteorology/radiation estimate, not an in-field sensor and not a forecast.",
            f"Meteorology cell {met_support.footprint_km_ns:.0f} x {met_support.footprint_km_ew:.0f} km; solar cell 1x1 deg: "
            "neither resolves farm-scale variation.",
            "Precipitation (PRECTOTCORR) is observation-corrected reanalysis; not independent of gauge-based products.",
        ] + (["SYNTHETIC DEMONSTRATION DATA - generated, not retrieved."] if is_synthetic else []),
        extras={
            "header_sources": header.get("sources"),
            "header_fill_value": fill,
            "response_coordinates_lon_lat_elev": geom,
            "met_cell_id": met_cell.cell_id,
            "solar_cell_id": sol_cell.cell_id,
            "community": req.community.upper(),
            "request_query": req.query(),
            "response_units": {p: (meta.get(p) or {}).get("units") for p in req.parameters},
            "elevation_note": "Elevation in the response (if any) is a grid-cell value, not the farm elevation.",
        },
    )
    return PowerParsed(series=series, evidence=evidence, warnings=warnings)


def _mode_to_series_mode(mode: str, synthetic: bool) -> str:
    if synthetic:
        return "fixture_synthetic"
    return {"live_fetch": "live_fetch", "cache_hit": "cache_hit", "stale_cache": "stale_cache",
            "fixture_real": "fixture_real"}.get(mode, mode)


def fetch_and_parse(req: PowerRequest, client: Optional[PowerClient] = None, *, force_refresh: bool = False) -> PowerParsed:
    client = client or PowerClient()
    got = client.fetch(req, force_refresh=force_refresh)
    return parse_power_payload(got.payload, req, url=got.url, retrieved_at_utc=got.retrieved_at_utc,
                               mode=got.mode, payload_sha256=got.payload_sha256)


_ = (canonical_json, sha256_text)
