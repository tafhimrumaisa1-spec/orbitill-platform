"""AgriPulse: small deterministic rule engine. Two classes only:
  review = something to check/decide soon (threshold crossed, blocked answer, disagreement)
  notice = informational / housekeeping (stale data, missing measurement, calendar)
No ML, no probabilities, no disaster or urgency wording. Every alert carries the evidence it was fired from."""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

from . import i18n
from .engine import stage_name
from .twin import (FarmTwin, evaluate_water_balance, get_farm_state, _planting_event, STALE_AFTER_DAYS,
                   MAX_ADVICE_LAG_DAYS, SOIL_TEST_STALE_DAYS)


def _alert(kind, klass, as_of, message, evidence, verify, sources, key=""):
    aid = "ap_" + hashlib.sha1(f"{kind}|{key}".encode()).hexdigest()[:10]
    return {"alert_id": aid, "kind": kind, "class": klass, "as_of": as_of.isoformat(), "message": message,
            "evidence": evidence, "suggested_verification": verify, "source_ids": sources,
            "not_a_forecast": True, "data_type": "model_estimate"}


def get_farm_alerts(twin: FarmTwin, as_of: date) -> list[dict]:
    out: list[dict] = []
    st = get_farm_state(twin, as_of)
    wr = evaluate_water_balance(twin, as_of, include_daily=True)
    planting = _planting_event(twin.events, as_of)
    lag = st["freshness"]["weather_lag_days"]

    # ---- stale gridded data
    if lag is None:
        out.append(_alert("outdated_nasa_data", "review", as_of, i18n.msg("alert.stale_weather", lag="unknown"),
                          [{"variable": "weather_lag_days", "value": None, "unit": "days", "data_type": "model_estimate"}],
                          ["load the latest gridded weather via EarthSync"], ["NASA_POWER"], "none"))
    elif lag > STALE_AFTER_DAYS:
        klass = "review" if lag > MAX_ADVICE_LAG_DAYS else "notice"
        out.append(_alert("outdated_nasa_data", klass, as_of, i18n.msg("alert.stale_weather", lag=lag),
                          [{"variable": "weather_lag_days", "value": lag, "unit": "days", "data_type": "model_estimate",
                            "last_weather_date": st["last_observation_dates"]["weather"]}],
                          ["refresh weather through EarthSync; add a farmer rain report for recent days"], ["NASA_POWER"], "stale"))

    # ---- blockers
    if wr["status"] == "verification_needed":
        for b in wr["blockers"]:
            if b["code"] == "NO_SOIL_CAPACITY":
                out.append(_alert("missing_measurement", "review", as_of, i18n.msg("alert.missing_soil_capacity"),
                                  [{"variable": "soil_capacity", "value": None, "unit": "m3/m3", "data_type": "farmer_reported"}],
                                  [b["required_input"]], ["FARMER_GROUND", "FAO56_ANNEX1_NV"], "soilcap"))
        return sorted(out, key=lambda a: (a["class"] != "review", a["kind"]))

    days = wr["daily"]
    last = days[-1]
    crop = wr["crop"]
    ws = wr["water_state"]

    # ---- threshold crossing
    if ws["model"] == "upland_root_zone":
        dr = ws["depletion_mm"]
        raw = ws["raw_mm"]
        if dr["low"] >= raw["high"]:
            crossed = None
            for dd in reversed(days):
                if dd["depletion_mm"] >= dd["raw_mm"]:
                    crossed = dd["date"]
                else:
                    break
            out.append(_alert("threshold_crossed", "review", as_of, i18n.msg("alert.threshold_crossed"),
                              [{"variable": "root_zone_depletion", "value": dr["low"], "unit": "mm", "data_type": "model_estimate"},
                               {"variable": "readily_available_water", "value": raw["high"], "unit": "mm", "data_type": "model_estimate"},
                               {"variable": "first_day_in_current_exceedance", "value": crossed, "unit": "date", "data_type": "model_estimate"}],
                              ["hand-feel or probe check at 15-30 cm", "log the result as a soil_test event"],
                              ["FAO56"], f"thr|{crossed}"))
    else:
        pd = ws["ponding_mm"]
        if pd["high"] <= 0:
            out.append(_alert("threshold_crossed", "review", as_of, i18n.msg("alert.ponding_low", ponding=round(pd["high"])),
                              [{"variable": "modeled_ponding_depth", "value": pd["high"], "unit": "mm", "data_type": "model_estimate"}],
                              ["read the field water tube", "log a field_water_depth event"], ["FAO_IDP_RICE_WATER", "WOCAT_AWD_BD"], "pond0"))
        elif pd["low"] <= 20:
            out.append(_alert("threshold_crossed", "notice", as_of, i18n.msg("alert.ponding_low", ponding=round(pd["low"])),
                              [{"variable": "modeled_ponding_depth", "value": pd["low"], "unit": "mm", "data_type": "model_estimate"}],
                              ["check the field"], ["FAO_IDP_RICE_WATER"], "pond20"))

    # ---- calendar review (entering mid stage within last 3 days)
    if crop:
        st_def = crop["stage_days"]
        mid_start = st_def["ini"] + st_def["dev"]
        dap = crop["days_after_planting"]
        if crop["stage"] == "mid" and 0 <= dap - mid_start <= 3:
            out.append(_alert("calendar_review", "notice", as_of, i18n.msg("alert.calendar_mid", stage="mid-season"),
                              [{"variable": "days_after_planting", "value": dap, "unit": "days", "data_type": "model_estimate"},
                               {"variable": "mid_stage_start_dap", "value": mid_start, "unit": "days", "data_type": "published_reference"}],
                              ["check soil moisture before and during this stage"], ["FAO56"], f"mid|{planting.date}"))
        if dap >= crop["expected_total_days"]:
            out.append(_alert("calendar_review", "notice", as_of, i18n.msg("alert.past_maturity"),
                              [{"variable": "days_after_planting", "value": dap, "unit": "days", "data_type": "model_estimate"}],
                              ["record harvest or correct the calendar"], ["FAO56"], "maturity"))

    # ---- missing measurements
    dsst = st["freshness"]["days_since_soil_test"]
    dap = crop["days_after_planting"]
    if (dsst is None and dap >= SOIL_TEST_STALE_DAYS) or (dsst is not None and dsst > SOIL_TEST_STALE_DAYS):
        out.append(_alert("missing_measurement", "notice", as_of, i18n.msg("alert.missing_soil_test", days=dsst if dsst is not None else dap),
                          [{"variable": "days_since_soil_test", "value": dsst, "unit": "days", "data_type": "farmer_reported"}],
                          ["do a hand-feel or probe check and log it"], ["FARMER_GROUND"], "soiltest"))
    if st["freshness"]["days_since_irrigation"] is None and dap >= 21:
        out.append(_alert("missing_measurement", "notice", as_of, i18n.msg("alert.missing_irrigation_log"),
                          [{"variable": "irrigation_events_logged", "value": 0, "unit": "count", "data_type": "farmer_reported"}],
                          ["add past irrigations (date, depth or pump hours)"], ["FARMER_GROUND"], "irrlog"))

    # ---- rain disagreement
    for dis in wr.get("rain_disagreements", []):
        out.append(_alert("rain_source_disagreement", "notice", as_of,
                          i18n.msg("alert.rain_disagreement", farmer=dis["farmer_mm"], gridded=dis["gridded_mm"], date=dis["date"]),
                          [{"variable": "farmer_rain", "value": dis["farmer_mm"], "unit": "mm", "data_type": "farmer_reported", "date": dis["date"]},
                           {"variable": "gridded_rain", "value": dis["gridded_mm"], "unit": "mm", "data_type": "model_estimate", "date": dis["date"]}],
                          ["no action; farmer report already used"], ["FARMER_GROUND", "NASA_POWER"], f"rain|{dis['date']}"))

    # ---- qualitative soil check vs model
    fc = [e for e in twin.events if e.kind == "soil_test" and e.payload.get("feel_class") and 0 <= (as_of - e.date).days <= 5]
    if fc and ws["model"] == "upland_root_zone":
        e = max(fc, key=lambda x: x.date)
        feel = e.payload["feel_class"]
        dr = ws["depletion_mm"]
        raw = ws["raw_mm"]
        mstate = "dry (at/below stress threshold)" if dr["low"] >= raw["high"] else ("wet (little depletion)" if dr["high"] <= 0.25 * raw["low"] else None)
        if mstate and ((feel == "wet" and mstate.startswith("dry")) or (feel == "dry" and mstate.startswith("wet"))):
            out.append(_alert("model_observation_disagreement", "review", as_of, i18n.msg("alert.model_obs_disagreement", feel=feel, state=mstate),
                              [{"variable": "feel_class", "value": feel, "unit": "category", "data_type": "farmer_reported", "date": e.date.isoformat()},
                               {"variable": "root_zone_depletion", "value": dr["low"], "unit": "mm", "data_type": "model_estimate"}],
                              ["measure with a probe and log theta_vol to re-anchor"], ["FARMER_GROUND", "FAO56"], f"mod|{e.date}"))

    # ---- allowance
    c = twin.profile.constraints
    if c.season_water_allowance_mm:
        used = sum(float(e.payload.get("depth_mm", 0)) for e in twin.events if e.kind == "irrigation" and e.date <= as_of)
        left = c.season_water_allowance_mm - used
        if left < 0.2 * c.season_water_allowance_mm:
            out.append(_alert("irrigation_calendar_review", "notice", as_of, i18n.msg("alert.allowance_low", left=round(max(left, 0))),
                              [{"variable": "allowance_remaining", "value": round(left, 1), "unit": "mm", "data_type": "farmer_reported"}],
                              ["re-plan remaining irrigations"], ["FARMER_GROUND"], "allow"))

    # ---- SMAP context disagreement (context only)
    if twin.smap_context and ws["model"] == "upland_root_zone":
        d0, theta, cls = sorted(twin.smap_context)[-1]
        dr = ws["depletion_mm"]
        raw = ws["raw_mm"]
        model_dry = dr["low"] >= raw["high"]
        model_wet = dr["high"] <= 0.25 * raw["low"]
        if cls and ((cls == "wet" and model_dry) or (cls == "dry" and model_wet)):
            out.append(_alert("context_disagreement", "notice", as_of, i18n.msg("alert.smap_context"),
                              [{"variable": "smap_surface_soil_moisture", "value": theta, "unit": "m3/m3", "data_type": "model_estimate",
                                "date": d0.isoformat() if hasattr(d0, "isoformat") else str(d0), "footprint": "9 km, top few cm"},
                               {"variable": "anomaly_class", "value": cls, "unit": "category", "data_type": "model_estimate"}],
                              ["field check; SMAP is not a root-zone measurement"], ["NASA_SMAP"], "smap"))
    return sorted(out, key=lambda a: (a["class"] != "review", a["kind"]))
