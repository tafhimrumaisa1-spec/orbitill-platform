"""Typed records for the TerraLens Region Intelligence Router.

The JSON wire format is camelCase and versioned. Every field that can be
missing is either explicitly ``None`` or carries a typed reason, so a consumer
never has to guess whether a blank means "zero" or "unknown".
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

SCHEMA_VERSION = "terralens.region_profile.v1"
SELECTION_SCHEMA_VERSION = "terralens.farm_selection.v1"
SOURCE_SCHEMA_VERSION = "terralens.source_register.v1"


class Readiness(str, Enum):
    """Mirrors ``orbitill-platform/services/science_api/contracts.py``.

    ``VALIDATED_WITH_EVIDENCE`` is defined for contract compatibility but is
    never emitted by this module: it would require field validation evidence
    that TerraLens does not own.
    """

    EXPLORATION = "exploration"
    CONDITIONAL = "conditional"
    RESEARCH_PILOT = "research_pilot"
    VALIDATED_WITH_EVIDENCE = "validated_with_evidence"


READINESS_ORDER = [
    Readiness.EXPLORATION,
    Readiness.CONDITIONAL,
    Readiness.RESEARCH_PILOT,
    Readiness.VALIDATED_WITH_EVIDENCE,
]


class Status(str, Enum):
    OK = "ok"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class Availability(str, Enum):
    AVAILABLE = "available"
    CONDITIONAL = "conditional"
    REQUIRES_INPUT = "requires_input"
    BLOCKED = "blocked"
    NOT_SCOPED = "not_scoped"


class Precision(str, Enum):
    FIELD_POLYGON = "field_polygon"
    POINT_APPROXIMATE = "point_approximate"


def _camel(name: str) -> str:
    return re.sub(r"_([a-z0-9])", lambda m: m.group(1).upper(), name)


def _ser(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        out = {}
        for f in value.__dataclass_fields__.values():  # type: ignore[attr-defined]
            item = getattr(value, f.name)
            out[_camel(f.name)] = _ser(item)
        return out
    if isinstance(value, dict):
        return {_camel(str(k)): _ser(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_ser(v) for v in value]
    return value


class Record:
    """Mixin: camelCase dict serialisation with enums flattened."""

    def to_dict(self) -> dict[str, Any]:
        return _ser(self)


@dataclass
class Insufficiency(Record):
    code: str
    message: str
    missing: list[str] = field(default_factory=list)
    remedy: str | None = None
    severity: str = "blocking"  # "blocking" | "warning" | "info"


@dataclass
class SourceRef(Record):
    id: str
    title: str
    provider: str
    license: str
    license_url: str
    url: str
    version: str
    used_for: str
    retrieved_at_utc: str | None = None
    sha256: str | None = None
    attribution: str | None = None


@dataclass
class LegendStop(Record):
    value: float
    color: str
    label: str


@dataclass
class Legend(Record):
    kind: str  # "gradient" | "classes" | "vector"
    unit: str
    native_resolution: str
    temporal: str
    stops: list[LegendStop] = field(default_factory=list)
    classes: list[dict[str, str]] = field(default_factory=list)
    note: str | None = None
    scale_note: str | None = None


@dataclass
class Layer(Record):
    id: str
    title: str
    title_bn: str
    group: str  # "boundaries" | "vegetation" | "water" | "soil" | "imagery" | "terrain" | "climate_grid"
    kind: str  # "vector" | "raster" | "grid"
    variable: str
    units: str
    native_resolution: str
    temporal_resolution: str
    aggregation: str
    data_type: str
    mode: str  # "offline" | "online"
    attribution: str
    license: str
    source_id: str
    caveat: str
    legend: Legend
    gibs_layer: str | None = None
    matrix_set: str | None = None
    matrix_level: int | None = None
    date_offset_days: int = 0
    geometry_file: str | None = None


@dataclass
class DatasetAvailability(Record):
    id: str
    name: str
    provider: str
    source_id: str
    license: str
    status: Availability
    readiness: Readiness
    native_resolution: str
    footprint_km: str | None
    temporal_resolution: str
    aggregation: str
    data_type: str
    layer_ids: list[str]
    access: str
    caveat: str
    is_field_measurement: bool = False


@dataclass
class AnalysisGate(Record):
    analysis: str
    status: Availability
    readiness: Readiness
    reasons: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    datasets: list[str] = field(default_factory=list)
    owner: str = "EarthSync"  # service that must supply the actual computation


@dataclass
class AdminUnitRef(Record):
    level: int
    id: str
    name: str
    name_bn: str | None
    role: str
    source_id: str
    license: str
    centroid: list[float] | None = None


@dataclass
class CountryRef(Record):
    id: str
    code: str
    name: str
    name_bn: str | None
    source_id: str
    license: str
    bbox: list[float]
    representative_point: list[float]


@dataclass
class RegionBlock(Record):
    region_id: str
    label: str
    label_bn: str
    mode: str
    readiness_cap: Readiness
    pack_status: str
    extent_basis: str
    description: str
    admin2_ids: list[str]
    approx_area_km2: float | None
    bbox: list[float] | None
    representative_point: list[float] | None
    parent_region_id: str | None = None


@dataclass
class LocationBlock(Record):
    lat: float
    lon: float
    on_land: bool
    country_code: str | None
    admin_depth: int
    inside_pilot_extent: bool
    nearest_admin_km: float | None
    bbox: list[float]


@dataclass
class FeatureFlags(Record):
    field_selection: bool
    upazila_browsing: bool
    county_browsing: bool
    salinity_gate: bool
    global_explorer: bool
    offline_atlas: bool
    online_raster_layers: bool
    crop_rules_in_router: bool = False
    claims_field_measurements: bool = False
    validated_region_pack: bool = False


@dataclass
class FarmerModeLink(Record):
    allowed: bool
    href: str
    reason: str | None = None


@dataclass
class TypedUnknown(Record):
    name: str
    state: str
    reason: str
    source_needed: str | None = None


@dataclass
class GridFootprint(Record):
    grid: str
    center_lat: float
    center_lon: float
    west: float
    south: float
    east: float
    north: float
    footprint_km_ns: float
    footprint_km_ew: float
    cell_id: str
    note: str


@dataclass
class RegionProfile(Record):
    schema_version: str
    generated_at_utc: str
    data_version: str
    status: Status
    query: dict[str, Any]
    location: LocationBlock
    country: CountryRef | None
    admin: list[AdminUnitRef]
    region: RegionBlock
    readiness_overall: Readiness
    analyses: dict[str, AnalysisGate]
    datasets: list[DatasetAvailability]
    feature_flags: FeatureFlags
    limitations: list[str]
    missing_requirements: list[str]
    unknowns: list[TypedUnknown]
    sources: list[SourceRef]
    footprints: dict[str, GridFootprint]
    farmer_mode: FarmerModeLink
    refusal: Insufficiency | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class FootprintComparison(Record):
    dataset_id: str
    label: str
    native_resolution: str
    field_share_of_cell: float | None
    field_spans: str
    note: str
    is_field_measurement: bool = False


@dataclass
class FarmSelection(Record):
    schema_version: str
    selection_id: str
    precision: Precision
    geometry: dict[str, Any]
    centroid: list[float]
    bbox: list[float]
    area_hectares: float | None
    area_acres: float | None
    perimeter_km: float | None
    region_id: str
    region_label: str
    admin: list[AdminUnitRef]
    country_code: str | None
    footprints: list[FootprintComparison]
    warnings: list[str]
    insufficiencies: list[Insufficiency]
    status: Status


@dataclass
class Envelope(Record):
    """Thin service envelope compatible with the shared contract's shape."""

    status: Status
    data: Any = None
    insufficiencies: list[Insufficiency] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    is_synthetic: bool = False
