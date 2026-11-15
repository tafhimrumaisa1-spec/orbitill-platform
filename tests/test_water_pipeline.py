from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "earthsync_runtime"))
sys.path.insert(0, str(ROOT / "modules" / "aquasense_runtime"))
sys.path.insert(0, str(ROOT))

from services.science_api.contracts import AnalysisStatus
from services.science_api.water_pipeline import evaluate_crop_season_water


FARM = {
    "farm_id": "test_explicit_inputs_only",
    "lat": 24.3745,
    "lon": 88.6042,
    "elevation_m": 20.0,
    "country": "BD",
    "area_ha": 1.0,
    "crop_id": "wheat",
    "soil": {
        "theta_fc": 0.30,
        "theta_wp": 0.15,
        "source": "test_explicit_input",
        "data_type": "hypothetical_scenario",
        "root_limit_m": 1.0,
    },
    "constraints": {
        "irrigation_method": "surface",
        "application_efficiency": 0.60,
        "max_irrigation_mm_per_event": 60.0,
        "season_water_allowance_mm": 300.0,
    },
    "admin_id": "BD-RAJ-BARIND",
}

STAGES = {
    "ini": 15,
    "dev": 25,
    "mid": 50,
    "late": 30,
    "source": "test_explicit_calendar",
    "status": "external_validated_calendar",
}


def run(**overrides):
    request = {
        "pilot_id": "BD-RAJ-BARIND",
        "crop_id": "wheat",
        "planting_date": "2023-11-15",
        "farm": FARM,
        "stage_days": STAGES,
    }
    request.update(overrides)
    return evaluate_crop_season_water(**request)


def test_real_weather_crop_season_runs_with_visible_conditional_status():
    result = run()

    assert result.status == AnalysisStatus.CONDITIONAL
    assert result.is_synthetic is False
    assert result.evidence_ids
    assert result.data["demand"]["season_complete"] is True
    assert result.data["irrigation"]["status"] == "conditional"
    assert result.data["scenario"]["kind"] == "historical_weather_analog"


def test_climate_and_allowance_changes_recompute_model_and_outputs():
    baseline = run()
    dry = run(rainfall_multiplier=0.5)
    restricted = run(irrigation_allowance_multiplier=0.5)

    assert len({baseline.model_run_id, dry.model_run_id, restricted.model_run_id}) == 3
    assert dry.is_synthetic is True
    assert dry.data["scenario"]["kind"] == "hypothetical_stress_test"
    base_policy = baseline.data["irrigation"]["policies"]["refill_at_raw"]
    dry_policy = dry.data["irrigation"]["policies"]["refill_at_raw"]
    restricted_policy = restricted.data["irrigation"]["policies"]["refill_at_raw"]
    assert dry_policy["rain_mm"]["value"] < base_policy["rain_mm"]["value"]
    assert restricted_policy["allowance_remaining_mm"] != base_policy["allowance_remaining_mm"]


def test_missing_soil_is_refused_not_defaulted():
    missing = {**FARM, "soil": {"source": "unknown"}}
    result = run(farm=missing)

    assert result.status == AnalysisStatus.REFUSED
    assert "farm.soil.theta_fc" in result.insufficiencies[0].missing


def test_invalid_physics_and_cross_region_binding_are_refused():
    bad_soil = {**FARM, "soil": {**FARM["soil"], "theta_wp": 0.35}}
    wrong_region = {**FARM, "admin_id": "BD-COASTAL"}

    assert run(farm=bad_soil).status == AnalysisStatus.REFUSED
    assert run(farm=wrong_region).status == AnalysisStatus.REFUSED
    assert run(stage_days={**STAGES, "mid": -1}).status == AnalysisStatus.REFUSED
