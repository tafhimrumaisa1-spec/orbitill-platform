from datetime import date

from aquasense.models import DailyWeather
from services.science_api.contracts import AnalysisStatus, model_run_id
from services.science_api.validation import (
    validate_daily_weather,
    validate_non_negative,
    validate_region_binding,
)


def complete_weather():
    return DailyWeather(
        date=date(2026, 1, 1),
        tmax_c=28,
        tmin_c=18,
        tdew_c=14,
        wind_2m_ms=2,
        solar_mj_m2_day=18,
        precip_mm=1,
    )


def test_model_run_id_changes_with_scientific_inputs_and_evidence():
    baseline = model_run_id(
        inputs={"rain_mm": [1, 2]},
        evidence_ids=["ev:power:a"],
        model_versions={"water": "1"},
    )
    changed_input = model_run_id(
        inputs={"rain_mm": [1, 3]},
        evidence_ids=["ev:power:a"],
        model_versions={"water": "1"},
    )
    changed_evidence = model_run_id(
        inputs={"rain_mm": [1, 2]},
        evidence_ids=["ev:power:b"],
        model_versions={"water": "1"},
    )
    assert len({baseline, changed_input, changed_evidence}) == 3


def test_weather_dates_without_values_are_refused():
    rows = [DailyWeather(date=date(2026, 1, day)) for day in range(1, 11)]
    result = validate_daily_weather(rows)
    assert result.status is AnalysisStatus.REFUSED
    assert result.data.usable_days == 0


def test_usable_weather_passes():
    result = validate_daily_weather([complete_weather() for _ in range(10)])
    assert result.status is AnalysisStatus.OK
    assert result.data.fraction == 1


def test_region_mismatch_and_negative_allowance_are_refused():
    mismatch = validate_region_binding(
        farm_region_id="BD-RAJ-BARIND", selected_region_id="US-IA-STORY"
    )
    assert mismatch.status is AnalysisStatus.REFUSED
    assert validate_non_negative(-1, field_name="irrigation_allowance_mm").status is AnalysisStatus.REFUSED
    assert validate_non_negative(None, field_name="irrigation_allowance_mm").status is AnalysisStatus.CONDITIONAL
