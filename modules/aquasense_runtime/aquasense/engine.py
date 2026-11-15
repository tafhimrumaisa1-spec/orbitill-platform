"""Daily water-balance engine: FAO-56 upland root-zone depletion + a separate flooded-rice (paddy) ponding model.

Daily order of operations (identical every day, tested in tests/test_timestep.py):
  1. determine stage, Kc (piecewise FAO-56 curve), root depth Zr, depletion fraction p from days-after-planting
  2. apply a dated soil_test / field_water_depth anchor (measurement taken at start of day)
  3. apply simulated policy irrigation (only in what-if runs) then farmer-reported irrigation (net = gross x efficiency)
  4. choose rainfall: farmer-reported rain overrides gridded estimate; missing rain => unknown (P=0 *upper-bound* depletion + flag)
  5. ET0 (FAO-56 PM) -> ETc = Kc*ET0 ; Ks from START-of-day depletion (FAO-56 Eq. 84) ; ETa limited to available water
  6. Dr_i = Dr_{i-1} - (P-RO) - I + ETa + DP  (Eq. 85) with DP = excess above field capacity (Eq. 88) ; 0 <= Dr <= TAW

Paddy: H_i = H_{i-1} + P + I - ETc - PERC, spill above bund height, H<0 means soil drying below surface saturation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Optional

from .crops import CropWaterProfile
from .et0 import estimate_et0
from .models import DailyWeather, FarmEvent, FarmProfile

EPS = 1e-9
DEFAULT_EFFICIENCY = {"surface": 0.60, "sprinkler": 0.75, "drip": 0.90, "unknown": 0.60}
DEFAULT_EFF_NOTE = ("default application efficiency by method (surface 0.60, sprinkler 0.75, drip 0.90) is an "
                    "AquaSense engineering assumption consistent with commonly quoted FAO values; enter the farm's own value")
CSF_MIN_PONDING_MM = 20.0   # engineering assumption: continuous shallow flooding refills when depth <= 2 cm
UPLAND_STOP_DAYS_BEFORE_MATURITY = 10  # engineering assumption: no policy irrigation in the last 10 days of the calendar
RICE_DRAIN_DAYS_BEFORE_HARVEST = 14  # WOCAT/BRRI AWD protocol: stop irrigating ~2 weeks before harvest


def stage_name(dap: int, st) -> str:
    if dap < 0:
        return "pre_planting"
    if dap < st.ini:
        return "ini"
    if dap < st.ini + st.dev:
        return "dev"
    if dap < st.ini + st.dev + st.mid:
        return "mid"
    if dap < st.total:
        return "late"
    return "past_maturity"


def kc_at(dap: int, crop: CropWaterProfile) -> float:
    """FAO-56 single Kc curve: flat ini, linear dev, flat mid, linear late (Fig. 34)."""
    st = crop.stages
    s = stage_name(dap, st)
    if s == "ini" or s == "pre_planting":
        return crop.kc_ini
    if s == "dev":
        return crop.kc_ini + (dap - st.ini + 0.5) / st.dev * (crop.kc_mid - crop.kc_ini)
    if s == "mid":
        return crop.kc_mid
    if s == "late":
        return crop.kc_mid + (dap - (st.ini + st.dev + st.mid) + 0.5) / st.late * (crop.kc_end - crop.kc_mid)
    return crop.kc_end


def root_depth_m(dap: int, crop: CropWaterProfile, limit_m: Optional[float]) -> float:
    st = crop.stages
    zmax = crop.zr_max_nominal_m
    if limit_m is not None:
        zmax = min(zmax, limit_m)
    zmin = min(crop.zr_min_m, zmax)
    grow = st.ini + st.dev
    if dap >= grow:
        return zmax
    return zmin + (zmax - zmin) * (dap + 1) / grow


def scs_runoff_mm(p: float, cn: float) -> float:
    s = 25400.0 / cn - 254.0
    ia = 0.2 * s
    return 0.0 if p <= ia else (p - ia) ** 2 / (p - ia + s)


@dataclass
class DayRecord:
    date: str
    dap: int
    stage: str
    kc: float
    et0_mm: Optional[float]
    et0_quality: str
    etc_potential_mm: Optional[float]
    eta_mm: float
    rain_used_mm: Optional[float]
    rain_source: str            # NASA_POWER | farmer_reported | hypothetical_scenario | unknown
    irrigation_gross_mm: float
    irrigation_net_mm: float
    irrigation_origin: str      # none | farmer_reported | simulated_policy
    deep_percolation_mm: float  # upland DP ; paddy: spill (overflow) mm
    # upland
    zr_m: Optional[float] = None
    taw_mm: Optional[float] = None
    raw_mm: Optional[float] = None
    depletion_mm: Optional[float] = None
    ks: Optional[float] = None
    # paddy
    ponding_mm: Optional[float] = None
    percolation_mm: Optional[float] = None
    flags: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        for k, v in list(d.items()):
            if isinstance(v, float):
                d[k] = round(v, 3)
        return d


@dataclass
class SimResult:
    kind: str                       # upland | paddy
    days: list
    summary: dict
    assumptions: list
    gaps: dict
    rain_disagreements: list
    events_applied: list
    events_ignored: list

    def last(self) -> Optional[DayRecord]:
        return self.days[-1] if self.days else None


def _rain_for(day: date, wx: Optional[DailyWeather], farmer_rain: Optional[float]):
    """returns (mm|None, source, nasa_mm|None)"""
    nasa = None if wx is None else wx.precip_mm
    if farmer_rain is not None:
        return farmer_rain, "farmer_reported", nasa
    if wx is None or wx.precip_mm is None:
        return None, "unknown", nasa
    return wx.precip_mm, wx.precip_source if wx.precip_type != "hypothetical_scenario" else "hypothetical_scenario", nasa


def simulate(crop: CropWaterProfile, farm: FarmProfile, weather: list[DailyWeather], events: list[FarmEvent],
             planting_date: date, end_date: date, *, aw: Optional[float] = None, theta_fc: Optional[float] = None,
             perc_mm_day: Optional[float] = None, awd_dry_storage_mm: Optional[float] = None,
             initial_depletion_mm: Optional[float] = None, initial_ponding_mm: Optional[float] = None,
             policy: Optional[dict] = None) -> SimResult:
    """Run the daily balance from planting_date to end_date (inclusive), bounded by crop maturity and harvest event.

    `aw` (m3/m3) is theta_fc - theta_wp (upland). `perc_mm_day` required for paddy.
    `policy` e.g. {"name":"refill_at_raw","trigger":1.0} | {"name":"csf"} | {"name":"awd"}; None = replay observed events only.
    """
    kind = crop.kind
    wx_by = {w.date: w for w in weather}
    c = farm.constraints
    ea_default = c.application_efficiency
    assumptions: list[str] = []
    eff_flagged = False

    # index events
    by_day: dict[date, list[FarmEvent]] = {}
    for e in events:
        by_day.setdefault(e.date, []).append(e)
    harvest = min((e.date for e in events if e.kind == "harvest"), default=None)
    last_day = min(end_date, planting_date + timedelta(days=crop.stages.total - 1))
    if harvest and harvest < last_day:
        last_day = harvest

    days: list[DayRecord] = []
    gaps = {"et0_gap_filled_days": [], "rain_unknown_days": [], "no_weather_days": [], "et0_fallback_days": 0}
    disagreements: list[dict] = []
    applied: list[dict] = []
    ignored: list[dict] = []
    recent_et0: list[float] = []

    # state
    dr = None          # upland depletion
    H = None           # paddy ponding
    unmodelled_start = False
    if kind == "upland":
        dr = float(initial_depletion_mm) if initial_depletion_mm is not None else 0.0
    else:
        H = float(initial_ponding_mm) if initial_ponding_mm is not None else 50.0

    allowance = c.season_water_allowance_mm
    allowance_left = allowance
    total_irr_gross = total_irr_net = total_rain = total_et = total_etc = total_dp = 0.0
    stress_days = 0
    n_policy_irrigations = 0

    d = planting_date
    while d <= last_day:
        dap = (d - planting_date).days
        flags: list[str] = []
        st = stage_name(dap, crop.stages)
        kc = kc_at(dap, crop)
        wx = wx_by.get(d)
        evs = by_day.get(d, [])

        # --- ET0
        if wx is None:
            gaps["no_weather_days"].append(d.isoformat())
            res = None
        else:
            res = estimate_et0(tmax=wx.tmax_c, tmin=wx.tmin_c, rh_mean=wx.rh_mean_pct, tdew=wx.tdew_c,
                               u2=wx.wind_2m_ms, rs=wx.solar_mj_m2_day, lat_deg=farm.lat,
                               elevation_m=farm.elevation_m, d=d)
        if res is not None and res.et0_mm_day is not None:
            et0 = res.et0_mm_day
            q = res.quality
            if res.substitutions:
                gaps["et0_fallback_days"] += 1
                flags.append("et0_fallback:" + "; ".join(res.substitutions))
            recent_et0.append(et0)
        else:
            if recent_et0:
                et0 = sum(recent_et0[-7:]) / len(recent_et0[-7:])
                q = "gap_filled"
                gaps["et0_gap_filled_days"].append(d.isoformat())
                flags.append("et0_gap_filled_with_recent_mean")
            else:
                et0 = None
                q = "not_computed"
                flags.append("et0_unavailable")

        # --- rain
        farmer_rain = None
        for e in evs:
            if e.kind == "rainfall_report":
                farmer_rain = float(e.payload.get("rain_mm", 0.0))
                applied.append({"date": d.isoformat(), "kind": e.kind, "rain_mm": farmer_rain})
        rain, rsrc, nasa_rain = _rain_for(d, wx, farmer_rain)
        if farmer_rain is not None and nasa_rain is not None and abs(farmer_rain - nasa_rain) >= 10.0:
            disagreements.append({"date": d.isoformat(), "farmer_mm": farmer_rain, "gridded_mm": round(nasa_rain, 2),
                                  "note": "gridded ~0.5deg estimate vs point report; farmer report used"})
        if rain is None:
            gaps["rain_unknown_days"].append(d.isoformat())
            flags.append("rain_unknown_assumed_zero_upper_bound_depletion")
            p_eff = 0.0
        else:
            p_eff = rain
        total_rain += p_eff

        # --- irrigation (farmer reported)
        irr_gross = 0.0
        irr_net = 0.0
        irr_origin = "none"
        for e in evs:
            if e.kind == "irrigation":
                g = float(e.payload.get("depth_mm", 0.0))
                eff = e.payload.get("application_efficiency", ea_default)
                if eff is None:
                    eff = DEFAULT_EFFICIENCY.get(c.irrigation_method, 0.60)
                    eff_flagged = True
                irr_gross += g
                irr_net += g * eff
                irr_origin = "farmer_reported"
                applied.append({"date": d.isoformat(), "kind": "irrigation", "gross_mm": g, "efficiency": eff})

        # --- anchors
        if kind == "upland":
            zr = root_depth_m(dap, crop, farm.soil.root_limit_m)
            taw = 1000.0 * aw * zr if aw is not None else None
            etp = None if et0 is None else kc * et0
            p_frac = crop.p_table22 if etp is None else min(max(crop.p_table22 + 0.04 * (5.0 - etp), 0.1), 0.8)
            for e in evs:
                if e.kind == "soil_test" and "theta_vol" in e.payload:
                    if theta_fc is None:
                        ignored.append({"date": d.isoformat(), "kind": "soil_test", "reason": "needs theta_fc to convert to depletion"})
                    else:
                        dr = max(0.0, min(taw, 1000.0 * (theta_fc - float(e.payload["theta_vol"])) * zr))
                        applied.append({"date": d.isoformat(), "kind": "soil_test", "theta_vol": e.payload["theta_vol"],
                                        "anchored_depletion_mm": round(dr, 2)})
                elif e.kind == "soil_test":
                    applied.append({"date": d.isoformat(), "kind": "soil_test", "feel_class": e.payload.get("feel_class"),
                                    "note": "qualitative: consistency check only"})
            if dr > taw:
                dr = taw
            raw_mm = p_frac * taw
            # simulated policy irrigation (what-if only)
            if policy and policy.get("name") == "refill_at_raw" and dap < crop.stages.total - UPLAND_STOP_DAYS_BEFORE_MATURITY and dap >= 0:
                if dr >= raw_mm * policy.get("trigger", 1.0) - EPS:
                    need_net = dr
                    eff = ea_default if ea_default is not None else DEFAULT_EFFICIENCY.get(c.irrigation_method, 0.60)
                    if ea_default is None:
                        eff_flagged = True
                    gross = need_net / eff
                    if c.max_irrigation_mm_per_event is not None:
                        gross = min(gross, c.max_irrigation_mm_per_event)
                    if allowance_left is not None:
                        gross = min(gross, max(allowance_left, 0.0))
                    if gross > EPS:
                        irr_gross += gross
                        irr_net += gross * eff
                        irr_origin = "simulated_policy" if irr_origin == "none" else "farmer_reported+simulated_policy"
                        n_policy_irrigations += 1
                        if allowance_left is not None:
                            allowance_left -= gross
            ks = 1.0 if dr <= raw_mm else max(0.0, (taw - dr) / ((1.0 - p_frac) * taw)) if taw > 0 else 0.0
            etc_pot = etp if etp is not None else 0.0
            eta_demand = ks * etc_pot
            runoff = scs_runoff_mm(p_eff, c.curve_number) if (c.curve_number and p_eff > 0) else 0.0
            p_net = p_eff - runoff
            avail = max(taw - dr + p_net + irr_net, 0.0)
            eta = min(eta_demand, avail)
            if eta < eta_demand - 1e-6:
                flags.append("eta_limited_by_available_water(at_wilting_point)")
            dr_u = dr - p_net - irr_net + eta
            dp = max(0.0, -dr_u)
            dr_new = min(max(dr_u, 0.0), taw)
            if ks < 1.0 - 1e-9:
                stress_days += 1
                flags.append("water_stress_ks<1")
            if runoff > 0:
                flags.append(f"runoff_estimated_scs_cn={runoff:.1f}mm")
            rec = DayRecord(date=d.isoformat(), dap=dap, stage=st, kc=kc, et0_mm=et0, et0_quality=q,
                            etc_potential_mm=None if etp is None else etp, eta_mm=eta, rain_used_mm=rain, rain_source=rsrc,
                            irrigation_gross_mm=irr_gross, irrigation_net_mm=irr_net, irrigation_origin=irr_origin,
                            deep_percolation_mm=dp, zr_m=zr, taw_mm=taw, raw_mm=raw_mm, depletion_mm=dr_new, ks=ks, flags=flags)
            dr = dr_new
            total_et += eta
            total_etc += etc_pot
            total_dp += dp
        else:
            # ---------------- paddy
            etc = 0.0 if et0 is None else kc * et0
            perc = perc_mm_day if perc_mm_day is not None else 0.0
            for e in evs:
                if e.kind == "field_water_depth":
                    H = float(e.payload["water_depth_mm"])
                    applied.append({"date": d.isoformat(), "kind": "field_water_depth", "water_depth_mm": H})
            dry_store = awd_dry_storage_mm if awd_dry_storage_mm is not None else 0.0
            eff = ea_default if ea_default is not None else DEFAULT_EFFICIENCY.get(c.irrigation_method, 0.60)
            days_left = (last_day - d).days
            if policy and policy.get("name") in ("csf", "awd") and days_left >= RICE_DRAIN_DAYS_BEFORE_HARVEST and dap >= 0:
                trigger = CSF_MIN_PONDING_MM if policy["name"] == "csf" else -dry_store
                target = policy.get("target_mm", 50.0)
                if H <= trigger + EPS:
                    # irrigate so end-of-day depth ~ target after today's losses
                    need_net = max(target - H + etc + perc - p_eff, 0.0)
                    if ea_default is None:
                        eff_flagged = True
                    gross = need_net / eff
                    if c.max_irrigation_mm_per_event is not None:
                        gross = min(gross, c.max_irrigation_mm_per_event)
                    if allowance_left is not None:
                        gross = min(gross, max(allowance_left, 0.0))
                    if gross > EPS:
                        irr_gross += gross
                        irr_net += gross * eff
                        irr_origin = "simulated_policy" if irr_origin == "none" else "farmer_reported+simulated_policy"
                        n_policy_irrigations += 1
                        if allowance_left is not None:
                            allowance_left -= gross
            H_u = H + p_eff + irr_net - etc - perc
            cap = c.bund_height_mm if c.bund_height_mm is not None else 100.0
            spill = max(0.0, H_u - cap)
            H_new = min(H_u, cap)
            if H_new < 0:
                flags.append("no_standing_water(soil_drying; check field water tube)")
                stress_days += 1
            if spill > 0:
                flags.append("overflow_above_bund(lost water)")
            rec = DayRecord(date=d.isoformat(), dap=dap, stage=st, kc=kc, et0_mm=et0, et0_quality=q,
                            etc_potential_mm=etc if et0 is not None else None, eta_mm=etc, rain_used_mm=rain, rain_source=rsrc,
                            irrigation_gross_mm=irr_gross, irrigation_net_mm=irr_net, irrigation_origin=irr_origin,
                            deep_percolation_mm=spill, ponding_mm=H_new, percolation_mm=perc, flags=flags)
            H = H_new
            total_et += etc
            total_etc += etc
            total_dp += spill
        total_irr_gross += irr_gross
        total_irr_net += irr_net
        days.append(rec)
        d += timedelta(days=1)

    if eff_flagged:
        assumptions.append(DEFAULT_EFF_NOTE)
    if c.curve_number is None and kind == "upland":
        assumptions.append("runoff not estimated (no curve number): intense rain on clay soils may be over-counted as infiltration")
    summary = {
        "days_simulated": len(days),
        "first_date": days[0].date if days else None,
        "last_date": days[-1].date if days else None,
        "et0_total_mm": round(sum(x.et0_mm or 0.0 for x in days), 2),
        "etc_potential_total_mm": round(total_etc, 2),
        "eta_total_mm": round(total_et, 2),
        "rain_total_mm": round(total_rain, 2),
        "irrigation_gross_total_mm": round(total_irr_gross, 2),
        "irrigation_net_total_mm": round(total_irr_net, 2),
        "deep_percolation_or_spill_total_mm": round(total_dp, 2),
        "stress_days": stress_days,
        "n_policy_irrigations": n_policy_irrigations,
        "allowance_remaining_mm": None if allowance_left is None else round(allowance_left, 2),
    }
    return SimResult(kind=kind, days=days, summary=summary, assumptions=assumptions, gaps=gaps,
                     rain_disagreements=disagreements, events_applied=applied, events_ignored=ignored)
