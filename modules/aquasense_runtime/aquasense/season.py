"""Season-level water outputs for RootShift / FutureFields: crop water demand and policy-simulated irrigation need.

These are MODEL results over a supplied weather series (an observed historical year used as an analog, or a labelled
hypothetical scenario). They are not forecasts and carry no yield or profit claim."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from .crops import get_crop
from .engine import simulate, stage_name
from .errors import InvalidInput
from .models import DailyWeather, FarmProfile, MODEL_VERSION
from .twin import _param_sets, _band
from .units import mm_to_m3_per_ha


def estimate_crop_et(crop_id: str, farm: FarmProfile, weather: list[DailyWeather], planting_date: date,
                     stage_days: Optional[dict] = None) -> dict:
    """ETc = Kc x ET0 by stage over the crop calendar. Needs no soil data (water DEMAND, not deficit)."""
    crop = get_crop(crop_id, stage_days)
    if farm.country not in crop.region_scope:
        return {"status": "verification_needed", "reason": f"{crop_id} coefficients not valid for {farm.country}",
                "numbers_withheld": True}
    end = planting_date + timedelta(days=crop.stages.total - 1)
    have = [w for w in weather if planting_date <= w.date <= end]
    if not have:
        return {"status": "verification_needed", "reason": "no weather rows inside crop calendar", "numbers_withheld": True}
    ps = [{"aw": 0.1, "theta_fc": 0.3}] if crop.kind == "upland" else [{"perc_mm_day": 0.0, "awd_dry_storage_mm": 0.0}]
    r = simulate(crop, farm, weather, [], planting_date, end, aw=ps[0].get("aw"), theta_fc=ps[0].get("theta_fc"),
                 perc_mm_day=ps[0].get("perc_mm_day"), initial_ponding_mm=50.0)
    per: dict[str, dict] = {}
    for d in r.days:
        s = per.setdefault(d.stage, {"days": 0, "et0_mm": 0.0, "etc_mm": 0.0, "rain_mm": 0.0})
        s["days"] += 1
        s["et0_mm"] += d.et0_mm or 0.0
        s["etc_mm"] += d.etc_potential_mm or 0.0
        s["rain_mm"] += d.rain_used_mm or 0.0
    for s in per.values():
        for k in ("et0_mm", "etc_mm", "rain_mm"):
            s[k] = round(s[k], 1)
    covered = len(r.days)
    complete = covered == crop.stages.total
    hypo = any(w.precip_type == "hypothetical_scenario" or w.met_type == "hypothetical_scenario" for w in have)
    return {"status": "conditional", "model_version": MODEL_VERSION, "crop_id": crop_id, "planting_date": planting_date.isoformat(),
            "season_days_expected": crop.stages.total, "season_days_with_weather": covered, "season_complete": complete,
            "etc_total_mm": round(r.summary["etc_potential_total_mm"], 1), "et0_total_mm": r.summary["et0_total_mm"],
            "rain_total_mm": r.summary["rain_total_mm"], "by_stage": per, "etc_total_m3_per_ha": round(mm_to_m3_per_ha(r.summary["etc_potential_total_mm"])),
            "gaps": r.gaps, "includes_hypothetical_scenario": hypo, "data_type": "model_estimate",
            "stage_days_status": crop.stage_status(),
            "notes": ["potential crop ET (no water stress). Rain is NOT subtracted here; use estimate_season_irrigation for net need.",
                      "Kc not climate-adjusted; stage lengths per provenance status"]}


def estimate_season_irrigation(crop_id: str, farm: FarmProfile, weather: list[DailyWeather], planting_date: date, *,
                               policies: Optional[list] = None, stage_days: Optional[dict] = None,
                               initial_depletion_mm: Optional[float] = None) -> dict:
    """Simulate irrigation under named policies over one season. Upland: refill_at_raw. Paddy: csf and awd.
    Returns ranges across published/assumed parameter bounds. Honest refusal if soil/percolation basis is missing."""
    crop = get_crop(crop_id, stage_days)
    if farm.country not in crop.region_scope:
        return {"status": "verification_needed", "reason": f"{crop_id} coefficients not valid for {farm.country}", "numbers_withheld": True}
    sets, basis, asm, blk = _param_sets(crop, farm.soil)
    if blk:
        return {"status": "verification_needed", "blockers": blk, "numbers_withheld": True,
                "demand_only": estimate_crop_et(crop_id, farm, weather, planting_date, stage_days)}
    end = planting_date + timedelta(days=crop.stages.total - 1)
    have = [w for w in weather if planting_date <= w.date <= end]
    if len(have) < crop.stages.total:
        return {"status": "verification_needed", "reason": f"weather covers {len(have)} of {crop.stages.total} season days",
                "numbers_withheld": True}
    pols = policies or ([{"name": "refill_at_raw", "trigger": 1.0}] if crop.kind == "upland" else [{"name": "csf"}, {"name": "awd"}])
    res = {}
    per_run_gross = {}
    for pol in pols:
        runs = []
        for ps in sets:
            runs.append(simulate(crop, farm, weather, [], planting_date, end, aw=ps.get("aw"), theta_fc=ps.get("theta_fc"),
                                 perc_mm_day=ps.get("perc_mm_day"), awd_dry_storage_mm=ps.get("awd_dry_storage_mm"),
                                 initial_depletion_mm=initial_depletion_mm, initial_ponding_mm=50.0, policy=pol))
        key = pol["name"]
        per_run_gross[key] = [r.summary["irrigation_gross_total_mm"] for r in runs]
        etc = [r.summary["etc_potential_total_mm"] for r in runs]
        eta = [r.summary["eta_total_mm"] for r in runs]
        res[key] = {
            "irrigation_gross_mm": _band([r.summary["irrigation_gross_total_mm"] for r in runs]),
            "irrigation_gross_m3_per_ha": _band([mm_to_m3_per_ha(r.summary["irrigation_gross_total_mm"]) for r in runs]),
            "rain_mm": _band([r.summary["rain_total_mm"] for r in runs]),
            "etc_potential_mm": _band(etc), "eta_mm": _band(eta),
            "eta_over_etc": _band([a / b if b else 1.0 for a, b in zip(eta, etc)]),
            "n_irrigations": _band([r.summary["n_policy_irrigations"] for r in runs]),
            "stress_days": _band([r.summary["stress_days"] for r in runs]),
            "deep_percolation_or_spill_mm": _band([r.summary["deep_percolation_or_spill_total_mm"] for r in runs]),
            "allowance_remaining_mm": runs[0].summary["allowance_remaining_mm"],
        }
        for k in ("eta_over_etc",):
            res[key][k]["unit"] = "fraction"
        res[key]["irrigation_gross_m3_per_ha"]["unit"] = "m3/ha"
        res[key]["n_irrigations"]["unit"] = "count"
        res[key]["stress_days"]["unit"] = "days"
    out = {"status": "conditional", "model_version": MODEL_VERSION, "crop_id": crop_id, "planting_date": planting_date.isoformat(),
           "basis": basis, "policies": res, "assumptions": asm + runs[0].assumptions
           + (["stage lengths: " + crop.stage_status()] if crop.stage_status() != "external_validated_calendar" else []),
           "includes_hypothetical_scenario": any(w.precip_type == "hypothetical_scenario" or w.met_type == "hypothetical_scenario" for w in have),
           "data_type": "model_estimate",
           "limitations": ["policy-simulated, not what the farmer did", "not a yield, profit or saving prediction",
                           "Kc not climate-adjusted; policy irrigation stops by assumption (rice: last 14 days; upland: last 10 days of the calendar)"]}
    if "csf" in res and "awd" in res:
        # paired by parameter set (same percolation bound) so the two policies are compared like-for-like
        diffs = [c - a for c, a in zip(per_run_gross["csf"], per_run_gross["awd"])]
        out["awd_vs_csf_modeled_gross_mm_saved"] = {"low": round(min(diffs), 1), "high": round(max(diffs), 1), "unit": "mm",
            "paired_by": "percolation bound",
            "note": ("model-conditional (negative = AWD used slightly MORE water in the model): seepage is held constant during dry-down, so the main real AWD mechanism "
                     "(less percolation without ponding head) is NOT represented. Field trials report 20-25% (WOCAT/BRRI) - compare, do not equate")}
    return out
