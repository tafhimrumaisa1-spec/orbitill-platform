"""FAO-56 Penman-Monteith reference evapotranspiration (ET0) from gridded forcing.

Allen, Pereira, Raes, Smith (1998), FAO Irrigation and Drainage Paper 56. Equation numbers
below refer to that paper. ET0 is the evaporative *demand* of a hypothetical reference grass
surface; it is not crop ET (needs Kc), not a measured flux, and for flooded paddy a different
water balance applies (AquaSense owns that). Here it is only a physically meaningful *forcing
feature* derived from NASA POWER variables.

Inputs are daily: Tmax/Tmin (degC), Rs (MJ m-2 d-1), u2 (m s-1 at 2 m), humidity via exactly one of
actual vapour pressure ``ea`` (kPa), dew point (degC) or mean relative humidity (%), and location
(latitude, elevation or pressure). Arrays are numpy-broadcast; NaN in -> NaN out (never filled).
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

GSC = 0.0820            # solar constant, MJ m-2 min-1
SIGMA = 4.903e-9        # Stefan-Boltzmann, MJ K-4 m-2 d-1
ALBEDO = 0.23           # reference grass albedo (FAO-56)


def sat_vp(t_c):
    """Eq. 11: saturation vapour pressure (kPa)."""
    t = np.asarray(t_c, dtype=float)
    return 0.6108 * np.exp(17.27 * t / (t + 237.3))


def slope_svp(t_c):
    """Eq. 13: slope of saturation vapour pressure curve (kPa/degC)."""
    t = np.asarray(t_c, dtype=float)
    return 4098.0 * sat_vp(t) / (t + 237.3) ** 2


def pressure_from_elevation(z_m):
    """Eq. 7: atmospheric pressure (kPa)."""
    return 101.3 * ((293.0 - 0.0065 * np.asarray(z_m, dtype=float)) / 293.0) ** 5.26


def elevation_from_pressure(p_kpa):
    """Inverse of Eq. 7 (used only when elevation is unknown but surface pressure is given)."""
    p = np.asarray(p_kpa, dtype=float)
    return (293.0 - 293.0 * (p / 101.3) ** (1.0 / 5.26)) / 0.0065


def psychrometric_constant(p_kpa):
    """Eq. 8 (kPa/degC)."""
    return 0.000665 * np.asarray(p_kpa, dtype=float)


def extraterrestrial_radiation(lat_deg: float, doy):
    """Eqs. 21-25: Ra (MJ m-2 d-1) for latitude and day of year."""
    j = np.asarray(doy, dtype=float)
    phi = math.radians(lat_deg)
    dr = 1.0 + 0.033 * np.cos(2.0 * math.pi * j / 365.0)
    delta = 0.409 * np.sin(2.0 * math.pi * j / 365.0 - 1.39)
    arg = np.clip(-math.tan(phi) * np.tan(delta), -1.0, 1.0)
    ws = np.arccos(arg)
    ra = (24.0 * 60.0 / math.pi) * GSC * dr * (ws * math.sin(phi) * np.sin(delta) + math.cos(phi) * np.cos(delta) * np.sin(ws))
    return np.maximum(ra, 0.0)


def daylight_hours(lat_deg: float, doy):
    """Eq. 34: maximum possible daylight hours N."""
    j = np.asarray(doy, dtype=float)
    phi = math.radians(lat_deg)
    delta = 0.409 * np.sin(2.0 * math.pi * j / 365.0 - 1.39)
    ws = np.arccos(np.clip(-math.tan(phi) * np.tan(delta), -1.0, 1.0))
    return 24.0 / math.pi * ws


def actual_vp(*, ea=None, tdew=None, rh_mean=None, tmax=None, tmin=None):
    """Actual vapour pressure from exactly one humidity route.

    Priority: explicit ea > dew point (Eq. 14) > mean RH (Eq. 19). Returns (ea, route_name).
    """
    if ea is not None:
        return np.asarray(ea, dtype=float), "ea_given"
    if tdew is not None:
        return sat_vp(tdew), "dewpoint_eq14"
    if rh_mean is not None and tmax is not None and tmin is not None:
        es = (sat_vp(tmax) + sat_vp(tmin)) / 2.0
        return np.asarray(rh_mean, dtype=float) / 100.0 * es, "rh_mean_eq19"
    raise ValueError("Need ea, tdew, or rh_mean (with tmax/tmin) to estimate actual vapour pressure")


def et0_pm_daily(tmax, tmin, rs, u2, lat_deg: float, doy, *, elevation_m: Optional[float] = None,
                 pressure_kpa=None, ea=None, tdew=None, rh_mean=None, g=0.0, return_parts: bool = False):
    """FAO-56 Penman-Monteith daily ET0 (mm/day), Eq. 6.

    Tmean = (Tmax+Tmin)/2 as FAO-56 prescribes for daily steps; G = 0 at daily step.
    Rs/Rso is bounded to [0.3, 1.0] (FAO-56 Eq. 39 guidance).
    """
    tmax = np.asarray(tmax, dtype=float)
    tmin = np.asarray(tmin, dtype=float)
    rs = np.asarray(rs, dtype=float)
    u2 = np.asarray(u2, dtype=float)
    tmean = (tmax + tmin) / 2.0
    if pressure_kpa is None:
        if elevation_m is None:
            raise ValueError("Provide elevation_m or pressure_kpa")
        pressure_kpa = pressure_from_elevation(elevation_m)
    p = np.asarray(pressure_kpa, dtype=float)
    z = elevation_m if elevation_m is not None else float(np.nanmean(elevation_from_pressure(p)))
    gamma = psychrometric_constant(p)
    es = (sat_vp(tmax) + sat_vp(tmin)) / 2.0                      # Eq. 12
    ea_v, route = actual_vp(ea=ea, tdew=tdew, rh_mean=rh_mean, tmax=tmax, tmin=tmin)
    delta = slope_svp(tmean)
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = (0.75 + 2e-5 * z) * ra                                   # Eq. 37
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.clip(np.where(rso > 0, rs / rso, np.nan), 0.3, 1.0)
    rns = (1.0 - ALBEDO) * rs                                       # Eq. 38
    rnl = SIGMA * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2.0 * (0.34 - 0.14 * np.sqrt(np.maximum(ea_v, 0))) * (1.35 * rel - 0.35)  # Eq. 39
    rn = rns - rnl                                                  # Eq. 40
    num = 0.408 * delta * (rn - g) + gamma * 900.0 / (tmean + 273.0) * u2 * (es - ea_v)
    den = delta + gamma * (1.0 + 0.34 * u2)
    et0 = np.maximum(num / den, 0.0)
    if return_parts:
        return et0, dict(tmean=tmean, es=es, ea=ea_v, ea_route=route, delta=delta, gamma=gamma, ra=ra, rso=rso, rns=rns, rnl=rnl, rn=rn, pressure=p, elevation_m=z)
    return et0
