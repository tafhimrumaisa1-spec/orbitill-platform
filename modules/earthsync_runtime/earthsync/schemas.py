"""Typed records for the EarthSync EvidenceFusion Data House.

These implement the shared-contract records ``Observation``, ``EvidenceRecord``,
``SourceManifest`` (``SourceManifestEntry``) and ``Feature`` plus two records the
contract implies but does not name: ``Insufficiency`` (typed "we do not know")
and ``EnvironmentalSeries`` (columnar container of many Observations that share
one provenance record).

Design rules enforced here
--------------------------
* Every value carries a ``data_type`` from the mission's closed vocabulary.
* Missing is ``None`` plus a flag, never a guessed number.
* Synthetic demonstration data is a first-class, *infectious* state:
  ``is_synthetic`` propagates from series to features to reports.
"""
from __future__ import annotations

import math
from datetime import date
from enum import Enum
from typing import Any, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"

# --- closed vocabularies -----------------------------------------------------
DataType = Literal[
    "observed",
    "farmer_reported",
    "published_reference",
    "model_estimate",
    "forecast",
    "hypothetical_scenario",
]

MeasurementProcess = Literal[
    "satellite_retrieval",       # e.g. SMAP, HLS reflectance, IMERG estimate
    "reanalysis_blend",          # e.g. MERRA-2 based POWER meteorology
    "satellite_model_blend",     # e.g. CERES/FLASHFlux based POWER radiation
    "gridded_interpolation",     # e.g. PRISM
    "ground_gauge",              # e.g. CoCoRaHS, USGS NWIS
    "model_simulation",          # e.g. GLDAS, OpenET
    "user_entry",                # farmer-reported
    "synthetic_demo",            # generated for demonstrations/tests only
]

RetrievalMode = Literal[
    "live_fetch",
    "cache_hit",
    "stale_cache",
    "fixture_real",              # bundled extract verifiably produced by fetch_real_fixtures.py
    "fixture_synthetic",         # bundled demonstration data, NOT a retrieval
    "user_supplied_extract",     # file the user downloaded from the provider
]


class InsufficiencyCode(str, Enum):
    missing_variable = "missing_variable"
    insufficient_coverage = "insufficient_coverage"
    source_unavailable = "source_unavailable"
    egress_blocked = "egress_blocked"
    offline_cache_miss = "offline_cache_miss"
    stale_data = "stale_data"
    unit_unrecognized = "unit_unrecognized"
    parameter_rejected = "parameter_rejected"
    invalid_response = "invalid_response"
    adapter_not_implemented = "adapter_not_implemented"
    not_applicable_for_region = "not_applicable_for_region"
    resolution_mismatch = "resolution_mismatch"
    synthetic_data_not_allowed = "synthetic_data_not_allowed"
    no_overlap = "no_overlap"
    sample_too_small = "sample_too_small"
    requires_credentials = "requires_credentials"
    requires_local_input = "requires_local_input"
    fixture_location_mismatch = "fixture_location_mismatch"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- small building blocks ---------------------------------------------------
class Insufficiency(_Model):
    """A typed, visible 'cannot conclude' result handed to downstream agents."""

    code: InsufficiencyCode
    message: str
    missing: list[str] = Field(default_factory=list)
    required_by: Optional[str] = None
    remedy: Optional[str] = None
    severity: Literal["blocking", "degrading"] = "blocking"


class SpatialSupport(_Model):
    kind: Literal["point", "grid_cell", "pixel", "polygon", "county", "region", "none"]
    requested_lat: Optional[float] = None
    requested_lon: Optional[float] = None
    native_resolution_lat_deg: Optional[float] = None
    native_resolution_lon_deg: Optional[float] = None
    native_resolution_m: Optional[float] = None
    footprint_bbox_wsen: Optional[tuple[float, float, float, float]] = None
    footprint_km_ns: Optional[float] = None
    footprint_km_ew: Optional[float] = None
    cell_id: Optional[str] = None
    note: Optional[str] = None


class TemporalSupport(_Model):
    step: Literal["hourly", "daily", "dekadal", "monthly", "annual", "overpass", "instant", "climatology"]
    time_standard: Literal["UTC", "LST", "provider_default", "not_applicable"] = "provider_default"
    start: Optional[str] = None
    end: Optional[str] = None
    latency_note: Optional[str] = None
    day_boundary_note: Optional[str] = None


class LicenseInfo(_Model):
    name: str
    url: Optional[str] = None
    attribution: Optional[str] = None
    verified: bool = False
    note: Optional[str] = None


class TransformationStep(_Model):
    step_id: str
    name: str
    version: str = "1"
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


# --- contract records --------------------------------------------------------
class EvidenceRecord(_Model):
    """Where a set of values came from, and everything that was done to them."""

    schema_version: str = SCHEMA_VERSION
    evidence_id: str
    source_id: str
    provider: str
    dataset_name: str
    dataset_version: Optional[str] = None
    original_url: Optional[str] = None
    citation: Optional[str] = None
    retrieved_at_utc: Optional[str] = None
    retrieval_mode: RetrievalMode
    spatial: SpatialSupport
    temporal: TemporalSupport
    variables: list[str] = Field(default_factory=list)
    transformations: list[TransformationStep] = Field(default_factory=list)
    license: LicenseInfo
    payload_sha256: Optional[str] = None
    adapter_version: Optional[str] = None
    is_synthetic: bool = False
    caveats: list[str] = Field(default_factory=list)
    downstream: list[str] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


class Observation(_Model):
    """One scalar observation. Prefer EnvironmentalSeries for bulk data."""

    schema_version: str = SCHEMA_VERSION
    observation_id: str
    source_id: str
    source_version: Optional[str] = None
    variable: str
    provider_variable: str
    value: Optional[float]
    unit: str
    observation_time: str
    ingestion_time: Optional[str] = None
    spatial: SpatialSupport
    quality_flags: list[str] = Field(default_factory=list)
    data_type: DataType
    measurement_process: MeasurementProcess
    evidence_id: str
    is_synthetic: bool = False


class EnvironmentalSeries(_Model):
    """Columnar daily (or other regular-step) series with shared provenance."""

    schema_version: str = SCHEMA_VERSION
    series_id: str
    source_id: str
    source_version: Optional[str] = None
    variable: str
    provider_variable: str
    unit: str
    dates: list[str]
    values: list[Optional[float]]
    flags: dict[str, list[str]] = Field(default_factory=dict)  # date -> flags
    spatial: SpatialSupport
    temporal: TemporalSupport
    data_type: DataType
    measurement_process: MeasurementProcess
    evidence_id: str
    retrieval_mode: RetrievalMode
    ingestion_time: Optional[str] = None
    is_synthetic: bool = False
    caveats: list[str] = Field(default_factory=list)

    # ---- convenience (not serialised) ----
    def as_array(self, start: Optional[str] = None, end: Optional[str] = None) -> tuple[list[str], np.ndarray]:
        """Dates and float array (NaN = missing) restricted to [start, end]."""
        ds, vs = [], []
        for d, v in zip(self.dates, self.values):
            if start is not None and d < start:
                continue
            if end is not None and d > end:
                continue
            ds.append(d)
            vs.append(np.nan if v is None else float(v))
        return ds, np.asarray(vs, dtype=float)

    def coverage(self, start: str, end: str) -> dict[str, Any]:
        """Coverage over the *requested* calendar window, not just stored days."""
        expected = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        _, arr = self.as_array(start, end)
        valid = int(np.isfinite(arr).sum())
        return {
            "expected_days": expected,
            "valid_days": valid,
            "missing_days": expected - valid,
            "fraction": (valid / expected) if expected > 0 else 0.0,
        }

    def observations(self, limit: Optional[int] = None) -> list[Observation]:
        out: list[Observation] = []
        for i, (d, v) in enumerate(zip(self.dates, self.values)):
            if limit is not None and i >= limit:
                break
            out.append(
                Observation(
                    observation_id=f"{self.series_id}@{d}",
                    source_id=self.source_id,
                    source_version=self.source_version,
                    variable=self.variable,
                    provider_variable=self.provider_variable,
                    value=v,
                    unit=self.unit,
                    observation_time=d,
                    ingestion_time=self.ingestion_time,
                    spatial=self.spatial,
                    quality_flags=self.flags.get(d, []) or (["missing"] if v is None else ["ok"]),
                    data_type=self.data_type,
                    measurement_process=self.measurement_process,
                    evidence_id=self.evidence_id,
                    is_synthetic=self.is_synthetic,
                )
            )
        return out


class Coverage(_Model):
    expected_days: int
    valid_days: int
    missing_days: int
    fraction: float


class Feature(_Model):
    """A physically meaningful quantity derived from NASA-centric series."""

    schema_version: str = SCHEMA_VERSION
    feature_id: str
    name: str
    family: Literal["water_input", "heat", "cold", "radiation", "evaporative_demand", "water_balance", "vegetation", "soil_moisture", "reliability", "other"]
    status: Literal["computed", "bounded", "insufficient"]
    value: Optional[float] = None
    value_lower: Optional[float] = None
    value_upper: Optional[float] = None
    unit: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    method_id: str
    method_version: str = "1"
    method_params: dict[str, Any] = Field(default_factory=dict)
    input_series_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: Optional[Coverage] = None
    insufficiency: list[Insufficiency] = Field(default_factory=list)
    data_type: DataType = "model_estimate"
    is_synthetic: bool = False
    spatial_note: Optional[str] = None
    caveats: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


class SourceManifestEntry(_Model):
    schema_version: str = SCHEMA_VERSION
    source_id: str
    name: str
    kind: Literal["dataset", "methodology", "access_service", "visual_only", "model_checkpoint", "user_input", "discovery_portal"]
    origin_group: str
    organizer_listed: bool = False
    organizer_name: Optional[str] = None
    # priority by geography (P0..P3, P1_STRETCH, N/A)
    priority_csv: str
    priority_bd: str
    priority_us: str
    priority_global: str
    applicability: dict[str, Literal["native", "limited", "not_applicable", "methodology_only", "user_supplied"]]
    coverage: str
    modules: list[str] = Field(default_factory=list)
    decision_role: str
    native_spatial: str
    native_temporal: str
    latency: Optional[str] = None
    variables: list[str] = Field(default_factory=list)
    access_method: str
    auth_required: Literal["none", "earthdata_login", "api_key", "registration", "manual_download", "unknown"]
    live_decision: Literal["live_implemented", "live_designed_untested", "offline_extract_ingest", "manifest_only", "do_not_use_live", "methodology_reference"]
    adapter_module: Optional[str] = None
    numerical_data: bool = True
    critical_caveat: str
    license: LicenseInfo
    official_url: str
    verification: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ProvenanceNode(_Model):
    node_id: str
    kind: Literal["source", "series", "transformation", "feature", "rule", "evaluation", "decision_input", "interpretation"]
    label: str
    detail: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(_Model):
    src: str
    dst: str
    relation: Literal["retrieved_as", "derived_by", "produces", "evaluated_against", "yields", "constrains", "explained_as"]


class ProvenanceGraph(_Model):
    schema_version: str = SCHEMA_VERSION
    graph_id: str
    nodes: list[ProvenanceNode]
    edges: list[ProvenanceEdge]


# --- helpers -----------------------------------------------------------------
def clean_floats(obj: Any) -> Any:
    """Make an object JSON-safe: NaN/inf -> None, numpy scalars -> python."""
    if isinstance(obj, dict):
        return {k: clean_floats(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean_floats(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj
