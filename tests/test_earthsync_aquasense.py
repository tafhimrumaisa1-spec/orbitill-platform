from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "modules" / "earthsync_runtime"))
sys.path.insert(0, str(ROOT / "modules" / "aquasense_runtime"))
sys.path.insert(0, str(ROOT))

from earthsync.access_policy import AccessPolicy
from earthsync.service import EarthSync
from services.science_api.earthsync_aquasense import (
    earthsync_observations_to_aquasense,
    earthsync_series_to_weather_bundle,
)


def test_synthetic_fixture_is_mapped_and_remains_labelled(tmp_path):
    service = EarthSync(
        AccessPolicy(offline=True, cache_dir=tmp_path / "cache")
    )
    result = service.get_environmental_series(
        24.3745,
        88.6042,
        "2023-11-01",
        "2023-11-07",
        (
            "PRECTOTCORR",
            "T2M_MAX",
            "T2M_MIN",
            "T2MDEW",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
        ),
        allow_fixture=True,
    )

    observations = [
        observation
        for series in service.series_objects(result).values()
        for observation in series.observations()
    ]
    weather = earthsync_observations_to_aquasense(observations)

    assert len(weather) == 7
    assert weather[0].precip_mm is not None
    assert weather[0].precip_type == "hypothetical_scenario"
    assert weather[0].met_source == "NASA_POWER"
    assert weather[0].ingested_at


def test_real_barind_fixture_is_discovered_and_lineage_survives(tmp_path):
    fixture_root = ROOT / "data" / "nasa-power"
    service = EarthSync(
        AccessPolicy(offline=True, cache_dir=tmp_path / "cache"),
        fixture_root=fixture_root,
    )
    result = service.get_environmental_series(
        24.3745,
        88.6042,
        "2023-11-01",
        "2023-11-07",
        (
            "PRECTOTCORR",
            "T2M_MAX",
            "T2M_MIN",
            "T2MDEW",
            "WS2M",
            "ALLSKY_SFC_SW_DWN",
        ),
    )

    assert result.status == "ok"
    assert result.is_synthetic is False
    assert result.retrieval["mode"] == "fixture_real"

    bundle = earthsync_series_to_weather_bundle(service.series_objects(result).values())
    assert len(bundle.rows) == 7
    assert bundle.is_synthetic is False
    assert bundle.source_ids == ("NASA_POWER",)
    assert len(bundle.evidence_ids) == 1
    assert bundle.time_standards == ("provider_default",)
    assert bundle.rows[0].precip_mm is not None
    assert bundle.rows[0].precip_type != "hypothetical_scenario"

