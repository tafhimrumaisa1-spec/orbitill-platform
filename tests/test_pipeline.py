from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "earthsync_runtime"))
sys.path.insert(0, str(ROOT / "modules" / "aquasense_runtime"))
sys.path.insert(0, str(ROOT))

from services.science_api.contracts import AnalysisStatus
from services.science_api.pipeline import load_pilot_weather


def test_barind_pipeline_returns_real_validated_weather_and_stable_run_id():
    first = load_pilot_weather("BD-RAJ-BARIND", "2023-11-01", "2023-11-07")
    second = load_pilot_weather("BD-RAJ-BARIND", "2023-11-01", "2023-11-07")

    assert first.status == AnalysisStatus.OK
    assert first.is_synthetic is False
    assert len(first.data["weather"]) == 7
    assert first.data["coverage"].fraction == 1.0
    assert first.data["retrieval"]["mode"] == "fixture_real"
    assert first.evidence_ids
    assert first.model_run_id == second.model_run_id


def test_pipeline_refuses_unverified_region_instead_of_substituting_data():
    result = load_pilot_weather("BD-COASTAL", "2023-11-01", "2023-11-07")

    assert result.status == AnalysisStatus.UNAVAILABLE
