"""Typed records shared across AquaSense. JSON-serialisable via .to_dict().

Data-type labels follow the shared mission: observed | farmer_reported | published_reference |
model_estimate | forecast | hypothetical_scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any, Optional

DATA_TYPES = ("observed", "farmer_reported", "published_reference", "model_estimate", "forecast",
              "hypothetical_scenario")

MODEL_VERSION = "aquasense-0.1.0"


def _d(v):
    return v.isoformat() if isinstance(v, date) else v


@dataclass(frozen=True)
class Observation:
    """EarthSync `Observation` (subset used here). AquaSense never fetches; it consumes these."""
    source_id: str                 # e.g. NASA_POWER, NASA_SMAP
    variable: str                  # e.g. PRECTOTCORR, T2M_MAX
    value: Optional[float]
    unit: str
    observed_on: date
    lat: float
    lon: float
    source_version: str = ""
    ingested_at: str = ""          # ISO timestamp
    native_resolution: str = ""    # e.g. "0.5x0.625 deg"
    quality_flags: tuple = ()
    data_type: str = "model_estimate"


@dataclass(frozen=True)
class DailyWeather:
    date: date
    tmax_c: Optional[float] = None
    tmin_c: Optional[float] = None
    rh_mean_pct: Optional[float] = None
    tdew_c: Optional[float] = None
    wind_2m_ms: Optional[float] = None
    solar_mj_m2_day: Optional[float] = None
    precip_mm: Optional[float] = None
    met_source: str = "NASA_POWER"
    met_type: str = "model_estimate"
    precip_source: str = "NASA_POWER"
    precip_type: str = "model_estimate"
    ingested_at: str = ""

    def to_dict(self):
        d = asdict(self)
        d["date"] = _d(self.date)
        return d


@dataclass
class SoilProfile:
    """Soil water capacity inputs. Nothing is invented: unknown stays None."""
    theta_fc: Optional[float] = None       # m3/m3 volumetric field capacity
    theta_wp: Optional[float] = None       # m3/m3 volumetric wilting point
    texture_class: Optional[str] = None    # key of FAO-56 Table 19 ranges
    source: str = "unknown"                # soil_test | farmer_reported_texture | unknown
    data_type: str = "farmer_reported"
    root_limit_m: Optional[float] = None   # hardpan / restricting layer depth
    percolation_mm_day: Optional[float] = None  # paddy: measured seepage+percolation
    percolation_source: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class FarmConstraints:
    irrigation_method: str = "unknown"             # surface | sprinkler | drip | unknown
    application_efficiency: Optional[float] = None  # 0-1; None -> flagged default
    max_irrigation_mm_per_event: Optional[float] = None   # pump/turn limit (farmer reported)
    season_water_allowance_mm: Optional[float] = None     # gross depth allowance (permit/diesel/aquifer)
    curve_number: Optional[float] = None            # optional SCS-CN for runoff; None = runoff not estimated
    bund_height_mm: Optional[float] = None          # paddy overflow height


@dataclass
class FarmProfile:
    farm_id: str
    lat: float
    lon: float
    elevation_m: float
    country: str                       # ISO-3166 alpha-2, e.g. BD, US
    area_ha: Optional[float] = None
    crop_id: Optional[str] = None
    soil: SoilProfile = field(default_factory=SoilProfile)
    constraints: FarmConstraints = field(default_factory=FarmConstraints)
    admin_id: str = ""

    def to_dict(self):
        return asdict(self)


EVENT_KINDS = ("planting", "transplanting", "irrigation", "rainfall_report", "soil_test",
               "field_water_depth", "harvest", "note")


@dataclass(frozen=True)
class FarmEvent:
    """Dated farmer-reported or measured event. Payload fields depend on kind:
    planting/transplanting: crop_id, initial_depletion_mm (optional), initial_water_depth_mm (paddy)
    irrigation:   depth_mm (gross at field), application_efficiency (optional), method (optional)
    rainfall_report: rain_mm (farmer gauge / observation, overrides NASA for that date)
    soil_test:    theta_vol (probe/gravimetric converted) -> anchors depletion | feel_class: dry|moist|wet -> consistency check only
    field_water_depth: water_depth_mm (paddy; positive ponded, negative = below surface via water tube)
    harvest:      ends the season
    """
    date: date
    kind: str
    payload: dict = field(default_factory=dict)
    source: str = "farmer_reported"      # farmer_reported | verified_measurement
    recorded_at: str = ""                # when entered (ISO); replay never uses it to reorder science
    event_id: str = ""

    def to_dict(self):
        return {"date": self.date.isoformat(), "kind": self.kind, "payload": self.payload,
                "source": self.source, "recorded_at": self.recorded_at, "event_id": self.event_id}
