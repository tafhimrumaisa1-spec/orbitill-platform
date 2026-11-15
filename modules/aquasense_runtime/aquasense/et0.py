"""FAO-56 reference evapotranspiration (ET0), Penman-Monteith, daily step.

Reference: Allen, Pereira, Raes, Smith (1998) FAO Irrigation & Drainage Paper 56, ch. 3-4, Annex 2.
Verified against the published worked Example 18 (Uccle/Brussels, 6 July): ET0 = 3.88 ~ 3.9 mm/day
(see tests/test_et0_fao56_example.py).

Fallbacks for incomplete NASA POWER rows follow FAO-56 ch. 3 guidance and are *flagged*:
  - missing wind  -> u2 = 2 m/s (FAO-56 default)
  - missing humidity/dew point -> ea = e0(Tmin) (FAO-56 Eq. 48 w/o the arid-climate 2 degC reduction)
  - missing solar radiation -> Hargreaves radiation Rs = krs*sqrt(Tmax-Tmin)*Ra (FAO-56 Eq. 50, krs=0.16 interior)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

GSC = 0.0820  # solar constant MJ m-2 min-1


def sat_vp(t_c: float) -> float:
    """Saturation vapour pressure e0(T), kPa  (FAO-56 Eq. 11)."""
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def slope_vp(t_c: float) -> float:
    """Slope of vapour pressure curve, kPa/degC (Eq. 13)."""
    return 4098.0 * sat_vp(t_c) / (t_c + 237.3) ** 2


def pressure_kpa(z_m: float) -> float:
    """Atmospheric pressure from elevation (Eq. 7)."""
    return 101.3 * ((293.0 - 0.0065 * z_m) / 293.0) ** 5.26


def psychrometric_const(p_kpa: float) -> float:
    return 0.000665 * p_kpa


def wind_to_2m(uz: float, z_m: float) -> float:
    """Log wind profile to 2 m (Eq. 47)."""
    return uz * 4.87 / math.log(67.8 * z_m - 5.42)


def day_of_year(d: date) -> int:
    return d.timetuple().tm_yday


def extraterrestrial_radiation(lat_deg: float, doy: int) -> float:
    """Ra, MJ m-2 day-1 (Eq. 21)."""
    phi = math.radians(lat_deg)
    dr = 1.0 + 0.033 * math.cos(2 * math.pi / 365 * doy)
    delta = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    x = -math.tan(phi) * math.tan(delta)
    ws = math.acos(max(-1.0, min(1.0, x)))
    return (24 * 60 / math.pi) * GSC * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))


def daylight_hours(lat_deg: float, doy: int) -> float:
    phi = math.radians(lat_deg)
    delta = 0.409 * math.sin(2 * math.pi / 365 * doy - 1.39)
    x = -math.tan(phi) * math.tan(delta)
    ws = math.acos(max(-1.0, min(1.0, x)))
    return 24.0 / math.pi * ws


def solar_from_sunshine(n_h: float, big_n_h: float, ra: float, a_s: float = 0.25, b_s: float = 0.50) -> float:
    return (a_s + b_s * n_h / big_n_h) * ra


def solar_hargreaves(tmax: float, tmin: float, ra: float, krs: float = 0.16) -> float:
    return krs * math.sqrt(max(tmax - tmin, 0.0)) * ra


def clear_sky_radiation(ra: float, z_m: float) -> float:
    return (0.75 + 2e-5 * z_m) * ra


def net_longwave(tmax: float, tmin: float, ea: float, rs: float, rso: float) -> float:
    sigma = 4.903e-9
    rel = min(max(rs / rso, 0.3), 1.0) if rso > 0 else 0.5
    return sigma * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2.0 * (0.34 - 0.14 * math.sqrt(max(ea, 0))) * (
        1.35 * rel - 0.35)


def ea_from_rh_extremes(tmax, tmin, rh_max, rh_min) -> float:  # Eq. 17
    return (sat_vp(tmin) * rh_max / 100.0 + sat_vp(tmax) * rh_min / 100.0) / 2.0


def ea_from_rh_mean(tmax, tmin, rh_mean) -> float:  # Eq. 19
    return rh_mean / 100.0 * (sat_vp(tmax) + sat_vp(tmin)) / 2.0


def ea_from_dewpoint(tdew) -> float:  # Eq. 14
    return sat_vp(tdew)


@dataclass
class ET0Result:
    et0_mm_day: float | None
    method: str
    quality: str  # full | reduced | poor | not_computed
    substitutions: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self):
        return {"et0_mm_day": None if self.et0_mm_day is None else round(self.et0_mm_day, 3),
                "method": self.method, "quality": self.quality,
                "substitutions": self.substitutions,
                "diagnostics": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.diagnostics.items()}}


def penman_monteith(*, tmax: float, tmin: float, ea: float, u2: float, rs: float, lat_deg: float,
                    elevation_m: float, doy: int, g: float = 0.0, albedo: float = 0.23) -> tuple[float, dict]:
    """Core FAO-56 Eq. 6 with all inputs resolved. Returns (ET0 mm/day, diagnostics)."""
    tmean = (tmax + tmin) / 2.0
    p = pressure_kpa(elevation_m)
    gamma = psychrometric_const(p)
    delta = slope_vp(tmean)
    es = (sat_vp(tmax) + sat_vp(tmin)) / 2.0
    ra = extraterrestrial_radiation(lat_deg, doy)
    rso = clear_sky_radiation(ra, elevation_m)
    rns = (1 - albedo) * rs
    rnl = net_longwave(tmax, tmin, ea, rs, rso)
    rn = rns - rnl
    num = 0.408 * delta * (rn - g) + gamma * 900.0 / (tmean + 273.0) * u2 * (es - ea)
    den = delta + gamma * (1 + 0.34 * u2)
    et0 = max(0.0, num / den)
    return et0, dict(tmean=tmean, pressure=p, gamma=gamma, delta=delta, es=es, ea=ea, ra=ra, rso=rso,
                     rns=rns, rnl=rnl, rn=rn, u2=u2, rs=rs)


def estimate_et0(*, tmax, tmin, rh_mean=None, tdew=None, u2=None, rs=None, lat_deg: float,
                 elevation_m: float, d: date, krs: float = 0.16) -> ET0Result:
    """ET0 from a (possibly incomplete) daily meteorological row; every substitution is reported."""
    if tmax is None or tmin is None:
        return ET0Result(None, "none", "not_computed", ["tmax/tmin missing: ET0 cannot be computed"])
    if tmax < tmin:
        return ET0Result(None, "none", "not_computed", ["tmax < tmin: invalid temperature pair"])
    doy = day_of_year(d)
    subs: list[str] = []
    ra = extraterrestrial_radiation(lat_deg, doy)
    if rs is None:
        rs = solar_hargreaves(tmax, tmin, ra, krs)
        subs.append(f"solar radiation estimated with Hargreaves (krs={krs}) [FAO-56 Eq. 50]")
    if tdew is not None:
        ea = ea_from_dewpoint(tdew)
    elif rh_mean is not None:
        ea = ea_from_rh_mean(tmax, tmin, rh_mean)
    else:
        ea = sat_vp(tmin)
        subs.append("humidity missing: ea = e0(Tmin) [FAO-56 Eq. 48]")
    if u2 is None:
        u2 = 2.0
        subs.append("wind missing: u2 = 2 m/s FAO-56 default")
    ea = min(ea, (sat_vp(tmax) + sat_vp(tmin)) / 2.0)  # ea cannot exceed es
    et0, diag = penman_monteith(tmax=tmax, tmin=tmin, ea=ea, u2=u2, rs=rs, lat_deg=lat_deg,
                                elevation_m=elevation_m, doy=doy)
    quality = "full" if not subs else ("reduced" if len(subs) == 1 else "poor")
    return ET0Result(et0, "FAO56-PM" if not subs else "FAO56-PM+fallbacks", quality, subs, diag)
