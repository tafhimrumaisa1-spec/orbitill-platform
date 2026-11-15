"""Unit helpers. Water depth is always millimetres internally; 1 mm over 1 ha = 10 m3."""
from __future__ import annotations

from .errors import InvalidInput, UnitError

M3_PER_HA_PER_MM = 10.0
SQM_PER_HA = 10_000.0
# 1 decimal (shotok/শতক) = 1/100 acre. Acre = 4046.8564224 m2.  Bigha is NOT a fixed unit in Bangladesh
# (commonly 33 decimals, but it varies by district/era) -> it must be supplied explicitly by the caller.
SQM_PER_ACRE = 4046.8564224
AREA_UNITS_SQM = {
    "m2": 1.0,
    "ha": SQM_PER_HA,
    "acre": SQM_PER_ACRE,
    "decimal": SQM_PER_ACRE / 100.0,
}


def area_to_ha(value: float, unit: str, bigha_decimals: float | None = None) -> float:
    if value is None or value <= 0:
        raise InvalidInput("area must be > 0", value=value, unit=unit)
    u = unit.lower()
    if u == "bigha":
        if not bigha_decimals:
            raise UnitError("bigha is not a fixed unit; supply bigha_decimals (e.g. 33) explicitly", unit=unit)
        return value * bigha_decimals * AREA_UNITS_SQM["decimal"] / SQM_PER_HA
    if u not in AREA_UNITS_SQM:
        raise UnitError(f"unsupported area unit {unit!r}", supported=list(AREA_UNITS_SQM) + ["bigha"])
    return value * AREA_UNITS_SQM[u] / SQM_PER_HA


def mm_to_m3_per_ha(mm: float) -> float:
    return mm * M3_PER_HA_PER_MM


def mm_to_m3(mm: float, area_ha: float) -> float:
    return mm * M3_PER_HA_PER_MM * area_ha


def pump_depth_mm(discharge_l_s: float, hours: float, area_ha: float) -> float:
    """Gross depth applied by a pump: Q*t / A.  10 L/s for 2 h on 0.2 ha -> 36 mm."""
    if discharge_l_s <= 0 or hours <= 0 or area_ha <= 0:
        raise InvalidInput("discharge, hours and area must be > 0",
                           discharge_l_s=discharge_l_s, hours=hours, area_ha=area_ha)
    m3 = discharge_l_s * 3600.0 * hours / 1000.0
    return m3 / (area_ha * SQM_PER_HA) * 1000.0


# Radiation / wind conversions used when consuming EarthSync Observations (units must be explicit).
def to_mj_m2_day(value: float, unit: str) -> float:
    u = unit.replace(" ", "").lower()
    table = {
        "mj/m^2/day": 1.0, "mj/m2/day": 1.0, "mjm-2day-1": 1.0, "mj/m²/day": 1.0,
        "kw-hr/m^2/day": 3.6, "kwh/m2/day": 3.6, "kwh/m^2/day": 3.6, "kwh/m²/day": 3.6,
        "w/m^2": 0.0864, "w/m2": 0.0864, "w/m²": 0.0864,  # daily mean flux -> MJ/m2/day
    }
    if u not in table:
        raise UnitError(f"unrecognised radiation unit {unit!r}", supported=sorted(table))
    return value * table[u]


def to_celsius(value: float, unit: str) -> float:
    u = unit.replace("°", "").replace(" ", "").lower()
    if u in ("c", "degc", "celsius"):
        return value
    if u in ("k", "kelvin"):
        return value - 273.15
    raise UnitError(f"unrecognised temperature unit {unit!r}")


def to_mm_day(value: float, unit: str) -> float:
    u = unit.replace(" ", "").lower()
    if u in ("mm/day", "mm/d", "mmday-1", "mm"):
        return value
    if u in ("kgm-2s-1", "kg/m^2/s", "kg/m2/s"):
        return value * 86400.0
    raise UnitError(f"unrecognised precipitation unit {unit!r}")


def to_ms(value: float, unit: str) -> float:
    u = unit.replace(" ", "").lower()
    if u in ("m/s", "ms-1", "m s-1"):
        return value
    if u in ("km/h", "kmh-1", "km/hr"):
        return value / 3.6
    raise UnitError(f"unrecognised wind unit {unit!r}")
