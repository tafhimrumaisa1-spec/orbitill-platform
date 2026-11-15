"""Unit normalisation driven by *provider metadata*, never by assumption.

NASA POWER reports ``ALLSKY_SFC_SW_DWN`` in MJ/m^2/day for community AG but
kW-hr/m^2/day for community RE/SB, so the adapter must read the unit string from
the response and convert; an unrecognised unit is a typed failure, not a guess.
"""
from __future__ import annotations

import re

from .schemas import Insufficiency, InsufficiencyCode


class UnitError(ValueError):
    def __init__(self, unit: str, target: str):
        super().__init__(f"Cannot convert unit {unit!r} to canonical {target!r}")
        self.unit, self.target = unit, target

    def to_insufficiency(self) -> Insufficiency:
        return Insufficiency(
            code=InsufficiencyCode.unit_unrecognized,
            message=str(self),
            missing=[self.unit],
            remedy="Add an explicit conversion with a source citation, or request a different community/format.",
        )


def _norm(u: str) -> str:
    u = u.strip().lower()
    u = u.replace("°", "").replace("º", "").replace("deg ", "").replace("degrees ", "")
    u = u.replace("^", "").replace(" ", "").replace("kw-hr", "kwh").replace("kw-h", "kwh")
    u = u.replace("m2", "m2").replace("/day", "/d").replace("/hr", "/h").replace("per", "/")
    u = u.replace("sq", "")
    return u


# canonical unit per dimension
CANON = {
    "temperature": "degC",
    "precip_depth": "mm/day",
    "irradiance_daily": "MJ/m2/day",
    "pressure": "kPa",
    "wind": "m/s",
    "rh": "%",
    "fraction": "1",
}

_TEMP = {"c", "degc", "celsius"}
_TEMP_F = {"f", "degf", "fahrenheit"}
_TEMP_K = {"k", "kelvin"}
_PREC_DAY = {"mm/d", "mm/day", "mmday-1"}
_PREC_HR = {"mm/h", "mm/hr"}
_RAD_MJ = {"mj/m2/d", "mjm-2d-1"}
_RAD_KWH = {"kwh/m2/d"}
_RAD_W = {"w/m2"}
_P_KPA = {"kpa"}
_P_PA = {"pa"}
_P_HPA = {"hpa", "mb", "mbar"}
_W_MS = {"m/s", "ms-1"}
_W_KMH = {"km/h", "kmh-1", "km/hr"}
_RH_PCT = {"%", "percent"}
_RH_FRAC = {"0to1", "fraction", "1"}


def to_canonical(value: float, unit: str, dimension: str) -> tuple[float, str, bool]:
    """Return (value, canonical_unit, was_converted). Raises UnitError if unknown."""
    u = _norm(unit)
    target = CANON[dimension]
    if dimension == "temperature":
        if u in _TEMP:
            return value, target, False
        if u in _TEMP_K:
            return value - 273.15, target, True
        if u in _TEMP_F:
            return (value - 32.0) * 5.0 / 9.0, target, True
    elif dimension == "precip_depth":
        if u in _PREC_DAY:
            return value, target, False
        # NOTE: mm/h is a *rate*; converting to a daily depth needs the averaging
        # period. Use rate_to_depth() explicitly. Never silently x24 here.
    elif dimension == "irradiance_daily":
        if u in _RAD_MJ:
            return value, target, False
        if u in _RAD_KWH:
            return value * 3.6, target, True
        if u in _RAD_W:  # daily-mean flux -> daily energy density
            return value * 0.0864, target, True
    elif dimension == "pressure":
        if u in _P_KPA:
            return value, target, False
        if u in _P_PA:
            return value / 1000.0, target, True
        if u in _P_HPA:
            return value / 10.0, target, True
    elif dimension == "wind":
        if u in _W_MS:
            return value, target, False
        if u in _W_KMH:
            return value / 3.6, target, True
    elif dimension == "rh":
        if u in _RH_PCT:
            return value, target, False
        if u in _RH_FRAC:
            return value * 100.0, target, True
    elif dimension == "fraction":
        if u in _RH_FRAC:
            return value, target, False
        if u in _RH_PCT:
            return value / 100.0, target, True
    raise UnitError(unit, target)


def rate_to_depth(rate_mm_per_hr: float, hours: float) -> float:
    """Depth (mm) accumulated by a constant rate over ``hours``.

    IMERG half-hourly fields are *rates* in mm/hr: each 30-min file represents
    rate*0.5 mm. A daily accumulation is the sum of 48 such depths, i.e.
    mean_rate*24, **not** the sum of 48 rates.
    """
    if hours < 0:
        raise ValueError("hours must be >= 0")
    return rate_mm_per_hr * hours


_ = re  # keep import for potential future parsing
