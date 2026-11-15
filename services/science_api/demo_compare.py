"""Judge-ready Barind comparison over real NASA POWER weather.

This is a research demonstration, not a farm recommendation. It deliberately
keeps the supplied soil, irrigation and crop-calendar assumptions visible.
"""

from __future__ import annotations

from typing import Any

from .contracts import model_run_id
from .water_pipeline import evaluate_crop_season_water


STRATEGIES = (
    {
        "id": "continue-boro",
        "label": "Continue",
        "rotation": "T. Aman → Boro rice",
        "crop_id": "boro_rice",
        "planting_date": "2025-01-10",
        "stage_days": {"ini": 30, "dev": 30, "mid": 60, "late": 30},
        "calendar_source": "FAO-56 Table 11 tropical rice analogue",
        "calendar_status": "unverified_placeholder",
        "policy": "awd",
    },
    {
        "id": "adapt-wheat",
        "label": "Adapt",
        "rotation": "T. Aman → Wheat",
        "crop_id": "wheat",
        "planting_date": "2024-11-20",
        "stage_days": {"ini": 15, "dev": 25, "mid": 50, "late": 30},
        "calendar_source": "FAO-56 Table 11 Central India analogue",
        "calendar_status": "published_reference_analogue",
        "policy": "refill_at_raw",
    },
    {
        "id": "diversify-mustard",
        "label": "Diversify",
        "rotation": "T. Aman → Mustard",
        "crop_id": "mustard",
        "planting_date": "2024-11-15",
        "stage_days": {"ini": 15, "dev": 20, "mid": 30, "late": 15},
        "calendar_source": "BARI Sarisha duration proxy with assumed stage split",
        "calendar_status": "unverified_placeholder",
        "policy": "refill_at_raw",
    },
)


def compare_barind_demo(*, rainfall_multiplier: float = 1.0, irrigation_allowance_mm: float = 700.0) -> dict[str, Any]:
    """Compare three explicitly conditional pathways under the same assumptions."""

    rain = _bounded(rainfall_multiplier, "rainfall_multiplier", 0.5, 1.5)
    allowance = _bounded(irrigation_allowance_mm, "irrigation_allowance_mm", 150.0, 1000.0)
    farm = _demo_farm(allowance)
    results = []

    for strategy in STRATEGIES:
        stage_days = {
            **strategy["stage_days"],
            "source": strategy["calendar_source"],
            "status": strategy["calendar_status"],
        }
        envelope = evaluate_crop_season_water(
            pilot_id="BD-RAJ-BARIND",
            crop_id=strategy["crop_id"],
            planting_date=strategy["planting_date"],
            farm=farm,
            stage_days=stage_days,
            rainfall_multiplier=rain,
        )
        results.append(_present(strategy, envelope.to_dict()))

    evidence_ids = sorted({evidence for result in results for evidence in result["evidence_ids"]})
    run_id = model_run_id(
        inputs={
            "pilot": "BD-RAJ-BARIND",
            "rainfall_multiplier": rain,
            "irrigation_allowance_mm": allowance,
            "farm_assumptions": farm,
            "strategies": STRATEGIES,
        },
        evidence_ids=evidence_ids,
        model_versions={"orbitill_demo_compare": "0.2.0", "aquasense": "0.1.0", "earthsync": "1.0.0"},
    )
    return {
        "schema": "orbitill.barind-comparison.v1",
        "status": "conditional",
        "model_run_id": run_id,
        "pilot": {"id": "BD-RAJ-BARIND", "label": "Barind Highlands research demonstration", "coordinates": [24.3745, 88.6042]},
        "scenario": {
            "kind": "historical_weather_analogue" if rain == 1.0 else "hypothetical_stress_test",
            "rainfall_multiplier": rain,
            "irrigation_allowance_mm": allowance,
            "not_a_forecast": True,
        },
        "assumptions": [
            "The 2024–2025 NASA POWER season is a historical weather analogue, not a forecast.",
            "Soil field capacity 0.30 and wilting point 0.15 m³/m³ are demonstration inputs, not a Barind field measurement.",
            "Surface-irrigation application efficiency 0.60 and the selected seasonal allowance are planning assumptions.",
            "Crop stage lengths are published analogues or visibly unverified placeholders; SoilBrain does not yet support a complete Barind calendar pack.",
        ],
        "results": results,
        "evidence": {
            "ids": evidence_ids,
            "provider": "NASA Langley Research Center POWER",
            "variables": ["PRECTOTCORR", "T2M_MAX", "T2M_MIN", "T2MDEW", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"],
            "observed_period": "2024-11-15 to 2025-06-08 (crop-dependent windows)",
            "retrieved": "2026-11-15T10:16:32Z",
            "native_support": "POWER daily point request; approximately 0.5° latitude × 0.625° longitude grid cell",
            "source_url": "https://power.larc.nasa.gov/",
        },
        "limitations": [
            "This compares water implications only; it does not rank profit, yield or overall agronomic suitability.",
            "NASA POWER is gridded data and cannot replace a field rain gauge, soil test or groundwater assessment.",
            "A pathway with lower simulated irrigation is not automatically the better farm decision.",
            "Coastal Bangladesh is outside this model and requires dated salinity evidence.",
        ],
    }


def _demo_farm(allowance: float) -> dict[str, Any]:
    return {
        "farm_id": "barind-guided-demo",
        "lat": 24.3745,
        "lon": 88.6042,
        "country": "BD",
        "elevation_m": 20.0,
        "admin_id": "BD-RAJ-BARIND",
        "area_ha": 0.2,
        "soil": {
            "theta_fc": 0.30,
            "theta_wp": 0.15,
            "source": "demonstration_assumption",
            "data_type": "hypothetical_scenario",
            "root_limit_m": 1.0,
        },
        "constraints": {
            "irrigation_method": "surface",
            "application_efficiency": 0.60,
            "max_irrigation_mm_per_event": 60.0,
            "season_water_allowance_mm": allowance,
        },
    }


def _present(strategy: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    data = envelope.get("data") or {}
    irrigation = data.get("irrigation") or {}
    policy = (irrigation.get("policies") or {}).get(strategy["policy"], {})
    gross = (policy.get("irrigation_gross_mm") or {}).get("value")
    demand = data.get("demand") or {}
    return {
        "id": strategy["id"],
        "label": strategy["label"],
        "rotation": strategy["rotation"],
        "status": envelope["status"],
        "model_run_id": envelope.get("model_run_id"),
        "planting_date": strategy["planting_date"],
        "season_end": data.get("season_end"),
        "calendar_status": strategy["calendar_status"],
        "calendar_source": strategy["calendar_source"],
        "irrigation_policy": strategy["policy"],
        "irrigation_gross_mm": gross,
        "rain_mm": demand.get("rain_total_mm"),
        "potential_crop_et_mm": demand.get("etc_total_mm"),
        "stress_days": (policy.get("stress_days") or {}).get("value"),
        "allowance_remaining_mm": policy.get("allowance_remaining_mm"),
        "evidence_ids": envelope.get("evidence_ids", []),
        "warnings": envelope.get("warnings", []),
        "limitations": envelope.get("limitations", []),
        "insufficiencies": envelope.get("insufficiencies", []),
    }


def _bounded(value: float, field: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    result = float(value)
    if not low <= result <= high:
        raise ValueError(f"{field} must be between {low:g} and {high:g}")
    return result
