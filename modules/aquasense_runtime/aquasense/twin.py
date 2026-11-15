"""FieldTwin Lite: event-sourced, timestamped farm state + AquaSense evaluation wrapper.

The twin is an *estimate* rebuilt by replaying dated events over a weather series. It is not live monitoring:
state is only as fresh as the last weather row and the last farmer entry, and both ages are reported.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Optional

from . import i18n
from .crops import CropWaterProfile, get_crop, texture_range, sources
from .engine import SimResult, simulate, stage_name, DEFAULT_EFFICIENCY
from .errors import ChronologyError, InvalidInput, UnsupportedCrop
from .models import (DailyWeather, FarmConstraints, FarmEvent, FarmProfile, SoilProfile, MODEL_VERSION, EVENT_KINDS)
from .units import mm_to_m3_per_ha

STALE_AFTER_DAYS = 7          # product rule for 'outdated weather', NOT a claim about NASA latency
MAX_ADVICE_LAG_DAYS = 10      # beyond this the 'do I need water' answer is withheld
MAX_CONSECUTIVE_ET_GAP = 3
RECENT_RAIN_UNKNOWN_DAYS = 3
SOIL_TEST_STALE_DAYS = 14     # product rule for 'missing measurement' notices


def _iso(d):
    return d.isoformat() if d else None


@dataclass(frozen=True)
class FarmTwin:
    profile: FarmProfile
    events: tuple = ()
    weather: tuple = ()
    stage_days_override: Optional[dict] = None   # e.g. SoilBrain calendar
    smap_context: tuple = ()                     # tuple of (date, theta_vol, anomaly_class|None) from EarthSync

    # ---- builders
    def with_weather(self, rows) -> "FarmTwin":
        ws = sorted(rows, key=lambda w: w.date)
        seen = set()
        for w in ws:
            if w.date in seen:
                raise InvalidInput("duplicate weather date", date=w.date.isoformat())
            seen.add(w.date)
        return replace(self, weather=tuple(ws))

    def fingerprint(self) -> str:
        blob = json.dumps({"p": self.profile.to_dict(), "e": [e.to_dict() for e in self.events],
                           "w": [w.to_dict() for w in self.weather], "s": self.stage_days_override}, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {"profile": self.profile.to_dict(), "events": [e.to_dict() for e in self.events],
                "weather": [w.to_dict() for w in self.weather], "stage_days_override": self.stage_days_override}


# ---------------------------------------------------------------- events
def validate_event(e: FarmEvent) -> None:
    if e.kind not in EVENT_KINDS:
        raise InvalidInput(f"unknown event kind {e.kind!r}", supported=list(EVENT_KINDS))
    p = e.payload
    if e.kind == "irrigation":
        dep = p.get("depth_mm")
        if dep is None or not (0 < dep <= 500):
            raise InvalidInput("irrigation needs depth_mm in (0, 500]", depth_mm=dep)
        eff = p.get("application_efficiency")
        if eff is not None and not (0 < eff <= 1):
            raise InvalidInput("application_efficiency must be in (0,1]", value=eff)
    elif e.kind == "rainfall_report":
        r = p.get("rain_mm")
        if r is None or not (0 <= r <= 1000):
            raise InvalidInput("rainfall_report needs rain_mm in [0, 1000]", rain_mm=r)
    elif e.kind == "soil_test":
        th = p.get("theta_vol")
        fc = p.get("feel_class")
        if th is None and fc is None:
            raise InvalidInput("soil_test needs theta_vol or feel_class")
        if th is not None and not (0.0 < th < 0.7):
            raise InvalidInput("theta_vol must be a volumetric fraction (0-0.7), not percent", theta_vol=th)
        if fc is not None and fc not in ("dry", "moist", "wet"):
            raise InvalidInput("feel_class must be dry|moist|wet", feel_class=fc)
    elif e.kind == "field_water_depth":
        if "water_depth_mm" not in p:
            raise InvalidInput("field_water_depth needs water_depth_mm")
    elif e.kind in ("planting", "transplanting"):
        if "crop_id" not in p:
            raise InvalidInput(f"{e.kind} needs crop_id")
        ind = p.get("initial_depletion_mm")
        if ind is not None and ind < 0:
            raise InvalidInput("initial_depletion_mm must be >= 0")
    if e.source not in ("farmer_reported", "verified_measurement"):
        raise InvalidInput("event source must be farmer_reported or verified_measurement", source=e.source)


def _event_id(e: FarmEvent) -> str:
    h = hashlib.sha1(json.dumps([e.date.isoformat(), e.kind, e.payload, e.source], sort_keys=True).encode()).hexdigest()[:10]
    return f"ev_{h}"


def apply_farm_event(twin: FarmTwin, event: FarmEvent) -> FarmTwin:
    """Return a NEW twin with the event appended (event sourcing). Back-dated entries are allowed; state is rebuilt by replay.
    Raises on malformed payloads, duplicate events, or events dated before the planting date (use initial_depletion_mm for
    pre-season water)."""
    validate_event(event)
    ev = event if event.event_id else replace(event, event_id=_event_id(event))
    if any(x.event_id == ev.event_id for x in twin.events):
        raise ChronologyError("duplicate event", event_id=ev.event_id)
    planting = _planting_event(twin.events, None)
    if ev.kind not in ("planting", "transplanting") and planting is not None and ev.date < planting.date:
        raise ChronologyError("event is dated before the planting date; put pre-season moisture in planting.initial_depletion_mm",
                              event_date=ev.date.isoformat(), planting=planting.date.isoformat())
    evs = sorted(list(twin.events) + [ev], key=lambda x: (x.date, EVENT_KINDS.index(x.kind), x.event_id))
    return replace(twin, events=tuple(evs))


def _planting_event(events, as_of: Optional[date]) -> Optional[FarmEvent]:
    cands = [e for e in events if e.kind in ("planting", "transplanting") and (as_of is None or e.date <= as_of)]
    return max(cands, key=lambda e: e.date) if cands else None


# ---------------------------------------------------------------- parameter bands
def _band(values: list) -> dict:
    vals = [v for v in values if v is not None]
    if not vals:
        return {"value": None, "low": None, "high": None, "unit": "mm"}
    lo, hi = min(vals), max(vals)
    return {"value": round(lo, 2) if abs(hi - lo) < 1e-9 else None, "low": round(lo, 2), "high": round(hi, 2), "unit": "mm"}


def _param_sets(crop: CropWaterProfile, soil: SoilProfile):
    """Return (list of parameter dicts, basis_label, assumptions list, blockers list)."""
    asm, blk = [], []
    if crop.kind == "upland":
        if soil.theta_fc is not None and soil.theta_wp is not None:
            if not (0 < soil.theta_wp < soil.theta_fc < 0.7):
                raise InvalidInput("need 0 < theta_wp < theta_fc < 0.7 (m3/m3)", theta_fc=soil.theta_fc, theta_wp=soil.theta_wp)
            return [{"aw": soil.theta_fc - soil.theta_wp, "theta_fc": soil.theta_fc}], "measured_or_supplied_capacity", asm, blk
        if soil.texture_class:
            t = texture_range(soil.texture_class)
            asm.append(f"soil capacity taken from FAO-56 Table 19 range for texture class '{soil.texture_class}' "
                       f"(available water {t['aw'][0]}-{t['aw'][1]} m3/m3); results are RANGES, not point values")
            return ([{"aw": t["aw"][0], "theta_fc": t["fc"][0]}, {"aw": t["aw"][1], "theta_fc": t["fc"][1]}],
                    "texture_class_range", asm, blk)
        blk.append({"code": "NO_SOIL_CAPACITY", "required_input": "soil texture class or soil test (field capacity & wilting point)",
                    "message": "Soil water capacity unknown: no root-zone mm can be computed."})
        return [], "unknown", asm, blk
    # paddy
    pad = crop.raw["paddy"]
    if soil.percolation_mm_day is not None:
        sets_p = [soil.percolation_mm_day]
        asm.append(f"percolation {soil.percolation_mm_day} mm/day supplied ({soil.percolation_source or 'source not stated'})")
    else:
        sets_p = [pad["percolation_mm_day"]["low"], pad["percolation_mm_day"]["high"]]
        asm.append("percolation+seepage unknown: bracketed with FAO published range "
                   f"{sets_p[0]}-{sets_p[1]} mm/day (heavy clay to sandy); Barind puddled soils need a local measurement")
    dry = [pad["awd_dry_storage_mm"]["low"], pad["awd_dry_storage_mm"]["high"]]
    out = []
    for pm in sets_p:
        out.append({"perc_mm_day": pm, "awd_dry_storage_mm": dry[0]})
    if len(sets_p) == 1:
        out.append({"perc_mm_day": sets_p[0], "awd_dry_storage_mm": dry[1]})
        out = out[:1]
    return out, ("supplied_percolation" if soil.percolation_mm_day is not None else "published_percolation_range"), asm, blk


def _crop_for(twin: FarmTwin, planting: Optional[FarmEvent]):
    cid = None
    if planting is not None:
        cid = planting.payload.get("crop_id")
    cid = cid or twin.profile.crop_id
    if not cid:
        return None, [{"code": "NO_CROP", "required_input": "crop", "message": "No crop selected."}]
    try:
        crop = get_crop(cid, twin.stage_days_override)
    except UnsupportedCrop as ex:
        return None, [{"code": "UNSUPPORTED_CROP", "required_input": "crop profile", "message": ex.message}]
    if twin.profile.country not in crop.region_scope:
        return None, [{"code": "CROP_NOT_VALID_FOR_REGION", "required_input": "region-valid crop coefficients",
                       "message": f"{cid} water coefficients are only provided for {crop.region_scope}; farm is in "
                                  f"{twin.profile.country}. Bangladeshi/US crop rules are never transplanted across countries."}]
    return crop, []


# ---------------------------------------------------------------- main evaluation
def evaluate_water_balance(twin: FarmTwin, as_of: date, *, include_daily: bool = False,
                           policy: Optional[dict] = None) -> dict:
    """Core entry point (AquaSense). Returns a provenance-rich dict; see schemas/water_balance_result.schema.json.
    Never raises for scientific insufficiency: returns status='verification_needed' with blockers instead."""
    planting = _planting_event(twin.events, as_of)
    crop, blockers = _crop_for(twin, planting)
    assumptions: list[str] = []
    advice_blockers: list[dict] = []
    wx = [w for w in twin.weather if w.date <= as_of]
    if planting is None:
        blockers.append({"code": "NO_PLANTING_DATE", "required_input": "planting or transplanting date",
                         "message": "No planting event on or before the as-of date."})
    if not wx:
        blockers.append({"code": "NO_WEATHER", "required_input": "daily weather (EarthSync NASA POWER series)",
                         "message": "No weather rows on or before the as-of date."})
    elif planting is not None and wx[-1].date < planting.date:
        blockers.append({"code": "WEATHER_BEFORE_PLANTING", "required_input": "weather covering the season",
                         "message": "Weather series ends before planting."})

    sets, basis, asm, blk = ([], "unknown", [], [])
    if crop is not None:
        sets, basis, asm, blk = _param_sets(crop, twin.profile.soil)
        assumptions += asm
        blockers += blk

    out = {
        "model_version": MODEL_VERSION, "as_of": as_of.isoformat(), "farm_id": twin.profile.farm_id,
        "input_hash": twin.fingerprint(), "method": "FAO-56 dual-step: PM ET0 x Kc, root-zone depletion (upland) / ponded water depth (paddy)",
        "status": None, "readiness": None, "blockers": blockers, "assumptions": assumptions, "warnings": [],
    }
    if blockers:
        out.update(status="verification_needed", readiness="exploration", numeric_validity="not_computed",
                   water_state=None, crop=None, answer=_answer_blocked(blockers), provenance=_provenance(twin, crop, None),
                   demand_only=_demand_only(twin, planting, crop, wx, as_of) if (crop and planting and wx) else None)
        return out

    end = min(as_of, wx[-1].date)
    ini_depl = planting.payload.get("initial_depletion_mm")
    ini_pond = planting.payload.get("initial_water_depth_mm")
    runs = []
    for ps in sets:
        r = simulate(crop, twin.profile, list(twin.weather), list(twin.events), planting.date, end,
                     aw=ps.get("aw"), theta_fc=ps.get("theta_fc"), perc_mm_day=ps.get("perc_mm_day"),
                     awd_dry_storage_mm=ps.get("awd_dry_storage_mm"), initial_depletion_mm=ini_depl,
                     initial_ponding_mm=ini_pond, policy=policy)
        runs.append(r)
    base = runs[0]
    last = [r.last() for r in runs]
    if not last or last[0] is None:
        out.update(status="verification_needed", readiness="exploration", numeric_validity="not_computed",
                   blockers=[{"code": "NO_SIMULATED_DAYS", "required_input": "weather on/after planting", "message": "Nothing to simulate."}],
                   water_state=None, crop=None, answer=_answer_blocked([{"required_input": "weather on/after planting"}]),
                   provenance=_provenance(twin, crop, None))
        return out

    gaps = base.gaps
    # --- consecutive ET gap
    consec = _max_consecutive(gaps["et0_gap_filled_days"] + gaps["no_weather_days"])
    if consec > MAX_CONSECUTIVE_ET_GAP or any("et0_unavailable" in f for d in base.days for f in d.flags):
        blockers.append({"code": "ET_GAP_TOO_LONG", "required_input": "temperature series without long gaps",
                         "message": f"{consec} consecutive days without usable ET0 inputs."})
    if blockers:
        out.update(status="verification_needed", readiness="exploration", numeric_validity="not_computed", water_state=None, crop=None,
                   answer=_answer_blocked(blockers), provenance=_provenance(twin, crop, base))
        return out

    # --- assumptions / validity
    if ini_depl is None and crop.kind == "upland" and not any(e.kind == "soil_test" and "theta_vol" in e.payload for e in twin.events if e.date <= as_of):
        assumptions.append("initial root-zone depletion unknown: planting assumed at field capacity (depletion 0). Optimistic for "
                           "residual-moisture rabi crops; a soil test re-anchors the estimate")
    if ini_pond is None and crop.kind == "paddy":
        assumptions.append("initial ponding unknown: assumed 50 mm at transplanting")
    sstat = crop.stage_status()
    if sstat in ("unverified_placeholder",):
        assumptions.append("stage lengths are placeholders (" + crop.raw["stage_days"].get("note", "") + ")")
    elif sstat == "published_reference":
        assumptions.append("stage lengths from a published non-local reference; confirm against the local variety calendar")
    assumptions += base.assumptions
    assumptions.append("Kc not adjusted for local RHmin/wind (FAO-56 Eq. 62) because POWER provides daily mean RH only")
    if gaps["et0_fallback_days"]:
        assumptions.append(f"{gaps['et0_fallback_days']} day(s) used ET0 fallbacks (see daily flags)")
    if gaps["et0_gap_filled_days"]:
        assumptions.append(f"{len(gaps['et0_gap_filled_days'])} day(s) gap-filled with the recent mean ET0")
    if gaps["rain_unknown_days"]:
        out["warnings"].append(f"rain unknown on {len(gaps['rain_unknown_days'])} day(s): treated as 0 mm, so depletion is an UPPER bound")
    hypo = any(w.precip_type == "hypothetical_scenario" or w.met_type == "hypothetical_scenario" for w in wx)

    # --- last-day state across bands
    d0 = last[0]
    state = {"crop_stage": d0.stage, "days_after_planting": d0.dap, "kc": round(d0.kc, 3), "data_type": "model_estimate"}
    if crop.kind == "upland":
        ws = {"model": "upland_root_zone", "depletion_mm": _band([x.depletion_mm for x in last]),
              "taw_mm": _band([x.taw_mm for x in last]), "raw_mm": _band([x.raw_mm for x in last]),
              "ks": {"low": round(min(x.ks for x in last), 3), "high": round(max(x.ks for x in last), 3)},
              "root_depth_m": round(d0.zr_m, 3), "data_type": "model_estimate"}
    else:
        ws = {"model": "paddy_ponding", "ponding_mm": _band([x.ponding_mm for x in last]),
              "percolation_mm_day": [r.days[-1].percolation_mm for r in runs], "data_type": "model_estimate"}
    totals = {k: _band_of(runs, k) for k in ("et0_total_mm", "etc_potential_total_mm", "eta_total_mm", "rain_total_mm",
                                             "irrigation_gross_total_mm", "deep_percolation_or_spill_total_mm")}
    # --- rain source tally
    tally: dict[str, int] = {}
    for dd in base.days:
        tally[dd.rain_source] = tally.get(dd.rain_source, 0) + 1

    lag = (as_of - wx[-1].date).days
    if lag > 0:
        out["warnings"].append(f"weather series ends {lag} day(s) before as-of; state is valid through {wx[-1].date.isoformat()}")

    # --- answer + advice
    advice_blockers = _advice_blockers(twin, as_of, base, lag, hypo)
    answer = _make_answer(crop, runs, last, twin, advice_blockers, hypo)

    # --- readiness
    cond_flags = bool(assumptions)
    soil_measured = (twin.profile.soil.source in ("soil_test",) and twin.profile.soil.theta_fc is not None) or \
                    (crop.kind == "paddy" and twin.profile.soil.percolation_mm_day is not None)
    readiness = "conditional"
    if soil_measured and sstat in ("external_validated_calendar", "published_reference") and gaps["et0_fallback_days"] == 0 \
            and not gaps["et0_gap_filled_days"] and twin.profile.constraints.application_efficiency is not None and not hypo \
            and not gaps["rain_unknown_days"]:
        readiness = "research_pilot"
    status = "conditional" if cond_flags or basis.endswith("range") else "ok"
    out.update(status=status, readiness=readiness,
               numeric_validity=("range_only" if len(runs) > 1 else "computed_with_assumptions"),
               validity_notes=("values are ranges across published/assumed parameter bounds" if len(runs) > 1 else
                               "single parameter set; assumptions listed"),
               crop={"crop_id": crop.crop_id, "names": crop.names, "kind": crop.kind, "planting_date": planting.date.isoformat(),
                     "stage": d0.stage, "days_after_planting": d0.dap, "expected_total_days": crop.stages.total,
                     "stage_days": {"ini": crop.stages.ini, "dev": crop.stages.dev, "mid": crop.stages.mid, "late": crop.stages.late},
                     "kc_today": round(d0.kc, 3), "kc_ini_mid_end": [crop.kc_ini, crop.kc_mid, crop.kc_end]},
               state_through=wx[-1].date.isoformat() if lag > 0 else end.isoformat(),
               water_state=ws, season_totals_mm=totals,
               rain_source_days=tally, rain_disagreements=base.rain_disagreements,
               events_applied=base.events_applied, events_ignored=base.events_ignored,
               gaps={k: v for k, v in gaps.items()}, includes_hypothetical_scenario=hypo,
               answer=answer, advice_withheld_reasons=advice_blockers,
               provenance=_provenance(twin, crop, base))
    if include_daily:
        out["daily"] = [x.to_dict() for x in base.days]
        if len(runs) > 1:
            out["daily_alt"] = [x.to_dict() for x in runs[-1].days]
    return out


def _band_of(runs: list[SimResult], key: str) -> dict:
    return _band([r.summary[key] for r in runs])


def _max_consecutive(day_strs: list[str]) -> int:
    if not day_strs:
        return 0
    ds = sorted(date.fromisoformat(x) for x in set(day_strs))
    best = cur = 1
    for a, b in zip(ds, ds[1:]):
        cur = cur + 1 if (b - a).days == 1 else 1
        best = max(best, cur)
    return best


def _advice_blockers(twin, as_of, base: SimResult, lag: int, hypo: bool) -> list:
    out = []
    if hypo:
        out.append("scenario_weather_in_series")
    if lag > MAX_ADVICE_LAG_DAYS:
        out.append(f"weather_lag_{lag}_days_exceeds_{MAX_ADVICE_LAG_DAYS}")
    last_days = {d.date for d in base.days[-RECENT_RAIN_UNKNOWN_DAYS:]}
    if any(x in last_days for x in base.gaps["rain_unknown_days"]):
        out.append("rain_unknown_in_last_3_days")
    return out


def _answer_blocked(blockers: list) -> dict:
    missing = "; ".join(b.get("required_input", b.get("code", "?")) for b in blockers)
    return {"verdict": "verification_needed", "message": i18n.msg("answer.verification_needed", missing=missing),
            "required_inputs": [b.get("required_input") for b in blockers], "numbers_withheld": True}


def _make_answer(crop, runs, last, twin, advice_blockers, hypo) -> dict:
    if hypo:
        inner = _make_answer(crop, runs, last, twin, [x for x in advice_blockers if x != "scenario_weather_in_series"], False)
        return {"verdict": "scenario_only", "message": i18n.msg("answer.scenario_only"), "numbers_withheld": False,
                "scenario_result": inner}
    if advice_blockers:
        return {"verdict": "verification_needed", "message": i18n.msg("answer.verification_needed",
                missing="; ".join(advice_blockers)), "required_inputs": advice_blockers, "numbers_withheld": False,
                "note": "numbers are shown for transparency but are not an irrigation recommendation"}
    if crop.kind == "paddy":
        H = min(x.ponding_mm for x in last)
        if H <= 0:
            return {"verdict": "irrigation_review", "message": i18n.msg("answer.paddy_review"), "numbers_withheld": False,
                    "verify_first": ["field water tube / soil surface"]}
        return {"verdict": "not_indicated", "message": i18n.msg("answer.paddy_ok", ponding=round(H)), "numbers_withheld": False}
    dr_hi = max(x.depletion_mm for x in last)
    raw_lo = min(x.raw_mm for x in last)
    dr_lo = min(x.depletion_mm for x in last)
    raw_hi = max(x.raw_mm for x in last)
    eff = twin.profile.constraints.application_efficiency or DEFAULT_EFFICIENCY.get(twin.profile.constraints.irrigation_method, 0.60)
    c = twin.profile.constraints
    if dr_lo >= raw_hi:      # all bands past threshold
        net = (dr_lo, dr_hi)
        gross = (net[0] / eff, net[1] / eff)
        limited = None
        if c.max_irrigation_mm_per_event is not None and gross[1] > c.max_irrigation_mm_per_event:
            limited = f"pump/turn limit {c.max_irrigation_mm_per_event} mm per event"
            gross = (min(gross[0], c.max_irrigation_mm_per_event), min(gross[1], c.max_irrigation_mm_per_event))
        gt = f"{gross[0]:.0f}-{gross[1]:.0f} mm gross ({mm_to_m3_per_ha(gross[0]):.0f}-{mm_to_m3_per_ha(gross[1]):.0f} m3/ha)" \
            if gross[1] - gross[0] > 1 else f"{gross[1]:.0f} mm gross ({mm_to_m3_per_ha(gross[1]):.0f} m3/ha)"
        return {"verdict": "irrigation_review", "message": i18n.msg("answer.irrigation_review", gross_text=gt),
                "net_refill_mm": {"low": round(net[0], 1), "high": round(net[1], 1)},
                "gross_mm": {"low": round(gross[0], 1), "high": round(gross[1], 1)},
                "gross_m3_per_ha": {"low": round(mm_to_m3_per_ha(gross[0])), "high": round(mm_to_m3_per_ha(gross[1]))},
                "efficiency_used": eff, "efficiency_is_default": c.application_efficiency is None,
                "limited_by": limited, "verify_first": ["hand-feel or probe check of the root zone"], "numbers_withheld": False}
    if dr_hi < raw_lo * 0.999 and dr_hi >= 0.5 * raw_lo:
        etc = _recent_etc(runs[0])
        d_txt = "no-rain persistence of recent ET reaches it in about " + (f"{(raw_lo - dr_hi) / etc:.0f} days" if etc > 0.1 else "an indeterminate time")
        return {"verdict": "monitor", "message": i18n.msg("answer.monitor", days_text=d_txt),
                "persistence_days_to_threshold": None if etc <= 0.1 else round((raw_lo - dr_hi) / etc, 1),
                "persistence_note": "hypothetical persistence of recent ET with no rain; not a forecast", "numbers_withheld": False}
    if dr_hi >= raw_lo:  # bands disagree
        return {"verdict": "verification_needed", "message": i18n.msg("answer.verification_needed",
                missing="soil capacity (estimate straddles the stress threshold; measure or narrow soil class)"),
                "required_inputs": ["soil test (field capacity, wilting point)"], "numbers_withheld": False}
    return {"verdict": "not_indicated", "message": i18n.msg("answer.not_indicated"), "numbers_withheld": False}


def _recent_etc(r: SimResult, n: int = 5) -> float:
    vals = [d.etc_potential_mm for d in r.days[-n:] if d.etc_potential_mm is not None]
    return sum(vals) / len(vals) if vals else 0.0


def _demand_only(twin, planting, crop, wx, as_of) -> dict:
    """When soil is unknown we may still report crop water *demand* (weather x Kc) which needs no soil data."""
    try:
        end = min(as_of, wx[-1].date)
        if end < planting.date:
            return None
        pol = None
        ps = [{"aw": 0.1, "theta_fc": 0.3}] if crop.kind == "upland" else [{"perc_mm_day": 0.0, "awd_dry_storage_mm": 0.0}]
        r = simulate(crop, twin.profile, list(twin.weather), list(twin.events), planting.date, end, aw=ps[0].get("aw"),
                     theta_fc=ps[0].get("theta_fc"), perc_mm_day=ps[0].get("perc_mm_day"), policy=pol)
        return {"etc_potential_total_mm": r.summary["etc_potential_total_mm"], "rain_total_mm": r.summary["rain_total_mm"],
                "note": "crop water DEMAND and rainfall only; no soil deficit or irrigation depth because soil capacity is unknown",
                "data_type": "model_estimate"}
    except Exception:
        return None


def _provenance(twin, crop, base) -> dict:
    wx = twin.weather
    return {
        "model_version": MODEL_VERSION,
        "weather": {"rows": len(wx), "first": _iso(wx[0].date) if wx else None, "last": _iso(wx[-1].date) if wx else None,
                    "met_sources": sorted({w.met_source for w in wx}), "met_types": sorted({w.met_type for w in wx}),
                    "precip_sources": sorted({w.precip_source for w in wx}), "precip_types": sorted({w.precip_type for w in wx}),
                    "last_ingested_at": max((w.ingested_at for w in wx if w.ingested_at), default=None),
                    "footprint_note": "NASA POWER MERRA-2 meteorology ~0.5 x 0.625 deg grid cell, CERES solar ~1 deg: not an in-field sensor and not a forecast"},
        "coefficients": crop.provenance() if crop else [],
        "sources": {k: sources()[k] for k in ("FAO56", "FAO56_EX18", "NASA_POWER") if k in sources()} | (
            {"FAO_IDP_RICE_WATER": sources()["FAO_IDP_RICE_WATER"], "WOCAT_AWD_BD": sources()["WOCAT_AWD_BD"]}
            if crop and crop.kind == "paddy" else {}),
        "soil": {"source": twin.profile.soil.source, "texture_class": twin.profile.soil.texture_class,
                 "theta_fc": twin.profile.soil.theta_fc, "theta_wp": twin.profile.soil.theta_wp},
        "limitations": [
            "Gridded weather is not an in-field sensor; local convective rain can differ strongly from the ~0.5 deg estimate.",
            "SMAP (9 km, top few cm) is context only and is NOT used in the root-zone balance.",
            "Groundwater level and water quality/salinity cannot be inferred from satellites; they require local well measurements.",
            "No yield, saving or profit is validated by this module.",
        ],
    }


# ---------------------------------------------------------------- FarmState
def get_farm_state(twin: FarmTwin, as_of: date) -> dict:
    """Estimated FarmState with freshness, missing inputs and timestamps (contract record `FarmState`)."""
    ev = [e for e in twin.events if e.date <= as_of]
    wr = evaluate_water_balance(twin, as_of)
    wx = [w for w in twin.weather if w.date <= as_of]

    def last_of(kind):
        ds = [e.date for e in ev if e.kind == kind]
        return max(ds) if ds else None
    planting = _planting_event(twin.events, as_of)
    last_wx = wx[-1].date if wx else None
    lag = (as_of - last_wx).days if last_wx else None
    missing = []
    if planting is None:
        missing.append("planting_date")
    soil = twin.profile.soil
    if wr["status"] == "verification_needed":
        missing += [b["required_input"] for b in wr["blockers"] if b["code"] not in ("NO_PLANTING_DATE",)]
    if soil.source == "unknown" and not soil.texture_class:
        missing.append("soil_water_capacity")
    if last_of("soil_test") is None:
        missing.append("soil_moisture_measurement")
    if last_of("irrigation") is None:
        missing.append("irrigation_log(no entries)")
    if twin.profile.constraints.application_efficiency is None:
        missing.append("irrigation_application_efficiency")
    if wr["status"] != "verification_needed":
        missing += ["groundwater_level_and_salinity(local test only)"]
    seen = []
    for m in missing:
        if m not in seen:
            seen.append(m)
    return {
        "farm_id": twin.profile.farm_id, "as_of": as_of.isoformat(), "model_version": MODEL_VERSION,
        "data_type": "model_estimate", "status": wr["status"], "readiness": wr["readiness"],
        "crop": wr.get("crop"), "water_state": wr.get("water_state"), "state_through": wr.get("state_through"),
        "last_observation_dates": {"weather": _iso(last_wx), "soil_test": _iso(last_of("soil_test")),
                                   "irrigation": _iso(last_of("irrigation")), "farmer_rain": _iso(last_of("rainfall_report")),
                                   "field_water_depth": _iso(last_of("field_water_depth")), "planting": _iso(planting.date) if planting else None},
        "freshness": {"weather_lag_days": lag, "weather_stale": (lag is None) or lag > STALE_AFTER_DAYS,
                      "stale_rule": f">{STALE_AFTER_DAYS} days is an AquaSense product rule, not a NASA latency claim",
                      "days_since_soil_test": None if last_of("soil_test") is None else (as_of - last_of("soil_test")).days,
                      "days_since_irrigation": None if last_of("irrigation") is None else (as_of - last_of("irrigation")).days},
        "missing_inputs": seen, "answer": wr["answer"], "assumptions": wr["assumptions"], "warnings": wr["warnings"],
        "events_count": len(ev), "input_hash": wr["input_hash"],
    }
