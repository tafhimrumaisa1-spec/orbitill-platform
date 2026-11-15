"""Crop-season water orchestration over evidence-backed environmental data."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
import math
from typing import Any

from aquasense.contract import profile_from_dict, weather_from_dicts
from aquasense.crops import get_crop
from aquasense.errors import AquaSenseError
from aquasense.scenarios import scale_rainfall
from aquasense.season import estimate_crop_et, estimate_season_irrigation

from .contracts import AnalysisStatus, Insufficiency, ServiceEnvelope, model_run_id
from .pipeline import PILOTS, load_pilot_weather
from .validation import validate_non_negative


def evaluate_crop_season_water(
    *,
    pilot_id: str,
    crop_id: str,
    planting_date: str,
    farm: dict[str, Any],
    stage_days: dict[str, Any],
    rainfall_multiplier: float = 1.0,
    irrigation_allowance_multiplier: float = 1.0,
) -> ServiceEnvelope:
    """Evaluate crop demand and policy irrigation using real pilot weather.

    Soil measurements, operational constraints and the local crop calendar are
    caller-owned evidence. This function never invents them. Scenario multipliers
    are explicit hypothetical stress tests, never forecasts.
    """

    for field, value in (
        ("rainfall_multiplier", rainfall_multiplier),
        ("irrigation_allowance_multiplier", irrigation_allowance_multiplier),
    ):
        checked = validate_non_negative(value, field_name=field)
        if checked.status == AnalysisStatus.REFUSED:
            return checked

    missing = _missing_required_inputs(farm, stage_days)
    if missing:
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            insufficiencies=(
                Insufficiency(
                    code="missing_crop_water_inputs",
                    message="A crop-season irrigation result requires explicit soil, efficiency and calendar inputs.",
                    missing=tuple(missing),
                    remedy="Supply measured or clearly labelled farmer-reported values; do not infer them from NASA weather.",
                ),
            ),
        )

    invalid = _invalid_physical_inputs(pilot_id, farm, stage_days)
    if invalid:
        return _invalid_request("; ".join(invalid))

    try:
        planted = date.fromisoformat(planting_date)
        crop = get_crop(crop_id, stage_days)
        profile = profile_from_dict(farm)
    except (AquaSenseError, KeyError, TypeError, ValueError) as exc:
        return _invalid_request(str(exc))

    expected_end = planted + timedelta(days=crop.stages.total - 1)
    weather_envelope = load_pilot_weather(pilot_id, planted.isoformat(), expected_end.isoformat())
    if weather_envelope.status != AnalysisStatus.OK:
        return weather_envelope

    weather = weather_from_dicts(weather_envelope.data["weather"])
    scenario_active = rainfall_multiplier != 1.0 or irrigation_allowance_multiplier != 1.0
    if rainfall_multiplier != 1.0:
        weather = scale_rainfall(
            weather,
            rainfall_multiplier,
            start=planted,
            end=expected_end,
            name="orbitill_rainfall_multiplier_",
        )

    if irrigation_allowance_multiplier != 1.0:
        allowance = profile.constraints.season_water_allowance_mm
        if allowance is None:
            return ServiceEnvelope(
                status=AnalysisStatus.REFUSED,
                insufficiencies=(
                    Insufficiency(
                        code="allowance_multiplier_without_baseline",
                        message="An irrigation allowance multiplier cannot be applied when the baseline allowance is unknown.",
                        missing=("farm.constraints.season_water_allowance_mm",),
                    ),
                ),
            )
        profile = replace(
            profile,
            constraints=replace(
                profile.constraints,
                season_water_allowance_mm=allowance * irrigation_allowance_multiplier,
            ),
        )

    demand = estimate_crop_et(crop_id, profile, weather, planted, stage_days)
    irrigation = estimate_season_irrigation(
        crop_id,
        profile,
        weather,
        planted,
        stage_days=stage_days,
    )
    if irrigation.get("status") == "verification_needed":
        blockers = tuple(
            item.get("required_input", item.get("code", "unknown"))
            for item in irrigation.get("blockers", [])
        )
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            data={"demand": demand},
            insufficiencies=(
                Insufficiency(
                    code="aquasense_verification_needed",
                    message=irrigation.get("reason", "AquaSense could not verify the season irrigation calculation."),
                    missing=blockers,
                ),
            ),
            evidence_ids=weather_envelope.evidence_ids,
            is_synthetic=scenario_active,
        )

    scientific_inputs = {
        "pilot_id": pilot_id,
        "crop_id": crop_id,
        "planting_date": planting_date,
        "farm": farm,
        "stage_days": stage_days,
        "rainfall_multiplier": rainfall_multiplier,
        "irrigation_allowance_multiplier": irrigation_allowance_multiplier,
        "weather_model_run_id": weather_envelope.model_run_id,
    }
    limitations = (
        "The crop calendar and farm/soil values are supplied inputs, not NASA observations.",
        "The irrigation result is a policy simulation, not a record of farmer actions or a yield forecast.",
        "NASA POWER represents a regional grid cell, not field rainfall or root-zone soil water.",
    )
    return ServiceEnvelope(
        status=AnalysisStatus.CONDITIONAL,
        data={
            "pilot_id": pilot_id,
            "crop_id": crop_id,
            "planting_date": planting_date,
            "season_end": expected_end.isoformat(),
            "scenario": {
                "active": scenario_active,
                "kind": "hypothetical_stress_test" if scenario_active else "historical_weather_analog",
                "rainfall_multiplier": rainfall_multiplier,
                "irrigation_allowance_multiplier": irrigation_allowance_multiplier,
            },
            "demand": demand,
            "irrigation": irrigation,
            "weather_model_run_id": weather_envelope.model_run_id,
        },
        model_run_id=model_run_id(
            inputs=scientific_inputs,
            evidence_ids=weather_envelope.evidence_ids,
            model_versions={
                "earthsync": "1.0.0",
                "aquasense": demand.get("model_version", "unknown"),
                "orbitill_water_pipeline": "0.1.0",
            },
        ),
        evidence_ids=weather_envelope.evidence_ids,
        is_synthetic=scenario_active,
        warnings=weather_envelope.warnings,
        limitations=limitations,
    )


def _missing_required_inputs(farm: dict[str, Any], stage_days: dict[str, Any]) -> list[str]:
    required = {
        "farm.lat": farm.get("lat"),
        "farm.lon": farm.get("lon"),
        "farm.country": farm.get("country"),
        "farm.elevation_m": farm.get("elevation_m"),
        "farm.soil.theta_fc": farm.get("soil", {}).get("theta_fc"),
        "farm.soil.theta_wp": farm.get("soil", {}).get("theta_wp"),
        "farm.constraints.application_efficiency": farm.get("constraints", {}).get("application_efficiency"),
        "stage_days.ini": stage_days.get("ini"),
        "stage_days.dev": stage_days.get("dev"),
        "stage_days.mid": stage_days.get("mid"),
        "stage_days.late": stage_days.get("late"),
        "stage_days.source": stage_days.get("source"),
    }
    return [key for key, value in required.items() if value is None or value == ""]


def _invalid_physical_inputs(
    pilot_id: str,
    farm: dict[str, Any],
    stage_days: dict[str, Any],
) -> list[str]:
    problems = []
    if pilot_id not in PILOTS:
        return problems  # The weather pipeline returns the typed unsupported-pilot result.
    if farm.get("admin_id") != pilot_id:
        problems.append("farm.admin_id must match pilot_id")

    soil = farm.get("soil", {})
    fc, wp = soil.get("theta_fc"), soil.get("theta_wp")
    if not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 < v < 1 for v in (fc, wp)):
        problems.append("theta_fc and theta_wp must be finite fractions between 0 and 1")
    elif wp >= fc:
        problems.append("theta_wp must be less than theta_fc")

    constraints = farm.get("constraints", {})
    efficiency = constraints.get("application_efficiency")
    if not isinstance(efficiency, (int, float)) or not math.isfinite(efficiency) or not 0 < efficiency <= 1:
        problems.append("application_efficiency must be greater than 0 and at most 1")
    for field in ("max_irrigation_mm_per_event", "season_water_allowance_mm"):
        value = constraints.get(field)
        if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            problems.append(f"{field} must be a non-negative number when supplied")

    for stage in ("ini", "dev", "mid", "late"):
        value = stage_days.get(stage)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0 or int(value) != value:
            problems.append(f"stage_days.{stage} must be a positive whole number")
    return problems


def _invalid_request(message: str) -> ServiceEnvelope:
    return ServiceEnvelope(
        status=AnalysisStatus.REFUSED,
        insufficiencies=(
            Insufficiency(code="invalid_crop_water_request", message=message),
        ),
    )
