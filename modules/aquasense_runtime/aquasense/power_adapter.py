"""Adapters from EarthSync/NASA POWER shaped data to AquaSense DailyWeather. AquaSense never fetches data itself.

POWER daily JSON (API v2): properties.parameter.<VAR>.<YYYYMMDD> = value; header.fill_value = -999;
parameters.<VAR>.units. Units must be present; unknown units raise UnitError rather than guessing."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional

from .errors import InvalidInput, UnitError
from .models import DailyWeather, Observation
from .units import to_celsius, to_mj_m2_day, to_mm_day, to_ms

POWER_VARS = {
    "T2M_MAX": ("tmax_c", to_celsius), "T2M_MIN": ("tmin_c", to_celsius), "T2MDEW": ("tdew_c", to_celsius),
    "RH2M": ("rh_mean_pct", lambda v, u: v), "WS2M": ("wind_2m_ms", to_ms),
    "ALLSKY_SFC_SW_DWN": ("solar_mj_m2_day", to_mj_m2_day), "PRECTOTCORR": ("precip_mm", to_mm_day),
}
FILL = -999.0


def observations_to_weather(obs: Iterable[Observation]) -> list[DailyWeather]:
    rows: dict[date, dict] = {}
    meta: dict[date, dict] = {}
    for o in obs:
        if o.variable not in POWER_VARS:
            continue
        field_name, conv = POWER_VARS[o.variable]
        r = rows.setdefault(o.observed_on, {})
        m = meta.setdefault(o.observed_on, {"ing": "", "src": o.source_id, "typ": o.data_type})
        m["ing"] = max(m["ing"], o.ingested_at)
        if o.value is None or o.value <= FILL + 1e-9 or "missing" in o.quality_flags or "fill_value" in o.quality_flags:
            r[field_name] = None
            continue
        r[field_name] = conv(float(o.value), o.unit)
    out = []
    for d in sorted(rows):
        m = meta[d]
        out.append(DailyWeather(date=d, met_source=m["src"], met_type=m["typ"], precip_source=m["src"], precip_type=m["typ"],
                                ingested_at=m["ing"], **rows[d]))
    return out


def parse_power_json(payload: dict, *, lat: Optional[float] = None, lon: Optional[float] = None,
                     ingested_at: str = "", source_version: str = "") -> list[DailyWeather]:
    try:
        par = payload["properties"]["parameter"]
        units = payload.get("parameters", {})
        fill = float(payload.get("header", {}).get("fill_value", FILL))
    except (KeyError, TypeError) as ex:
        raise InvalidInput("not a NASA POWER daily point JSON", missing=str(ex))
    if lon is None or lat is None:
        coords = payload.get("geometry", {}).get("coordinates", [None, None])
        lon, lat = coords[0], coords[1]
    obs = []
    for var, series in par.items():
        if var not in POWER_VARS:
            continue
        unit = (units.get(var) or {}).get("units")
        if not unit:
            raise UnitError(f"units missing for {var}; refuse to guess", variable=var)
        for ymd, v in series.items():
            d = datetime.strptime(ymd, "%Y%m%d").date()
            flags = ("fill_value",) if v is None or float(v) == fill else ()
            obs.append(Observation(source_id="NASA_POWER", variable=var, value=None if flags else float(v), unit=unit,
                                   observed_on=d, lat=lat, lon=lon, source_version=source_version, ingested_at=ingested_at,
                                   native_resolution="0.5x0.625 deg (MERRA-2) / 1x1 deg (CERES)", quality_flags=flags,
                                   data_type="model_estimate"))
    return observations_to_weather(obs)
