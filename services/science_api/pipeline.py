"""Evidence-preserving offline environmental pipeline for verified pilots."""

from __future__ import annotations

from pathlib import Path

from earthsync.access_policy import AccessPolicy
from earthsync.service import EarthSync

from .contracts import AnalysisStatus, Insufficiency, ServiceEnvelope, model_run_id
from .earthsync_aquasense import earthsync_series_to_weather_bundle
from .validation import validate_daily_weather


PLATFORM_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = PLATFORM_ROOT / "data" / "nasa-power"

PILOTS = {
    "BD-RAJ-BARIND": {"lat": 24.3745, "lon": 88.6042},
    "US-IA-STORY": {"lat": 42.0308, "lon": -93.6319},
}

WEATHER_VARIABLES = (
    "PRECTOTCORR",
    "T2M_MAX",
    "T2M_MIN",
    "T2MDEW",
    "RH2M",
    "WS2M",
    "ALLSKY_SFC_SW_DWN",
)


def load_pilot_weather(pilot_id: str, start: str, end: str) -> ServiceEnvelope:
    """Load a dated, real NASA POWER weather window without network access."""

    pilot = PILOTS.get(pilot_id)
    if pilot is None:
        return ServiceEnvelope(
            status=AnalysisStatus.UNAVAILABLE,
            insufficiencies=(
                Insufficiency(
                    code="unsupported_real_weather_pilot",
                    message=f"No verified offline NASA POWER bundle is registered for {pilot_id!r}.",
                    missing=("verified_environmental_bundle",),
                    remedy="Retrieve and verify a real regional bundle before enabling this analysis.",
                ),
            ),
        )

    service = EarthSync(
        AccessPolicy(offline=True, cache_dir=PLATFORM_ROOT / "data" / "cache"),
        fixture_root=FIXTURE_ROOT,
    )
    result = service.get_environmental_series(
        pilot["lat"], pilot["lon"], start, end, WEATHER_VARIABLES
    )
    if result.status != "ok" or result.is_synthetic:
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            insufficiencies=(
                Insufficiency(
                    code="real_weather_unavailable",
                    message="A complete, non-synthetic environmental window could not be loaded.",
                    missing=("real_daily_weather",),
                ),
            ),
            warnings=tuple(item.message for item in (*result.insufficiency, *result.warnings)),
            is_synthetic=result.is_synthetic,
        )

    bundle = earthsync_series_to_weather_bundle(service.series_objects(result).values())
    coverage = validate_daily_weather(bundle.rows)
    limitations = (
        "NASA POWER is gridded environmental data, not an in-field rain gauge or soil-water sensor.",
        "Provider-default daily boundaries are preserved and must be declared when compared with local reports.",
    )
    if coverage.status != AnalysisStatus.OK:
        return ServiceEnvelope(
            status=coverage.status,
            data=coverage.data,
            insufficiencies=coverage.insufficiencies,
            evidence_ids=bundle.evidence_ids,
            is_synthetic=bundle.is_synthetic,
            limitations=limitations,
        )

    weather = [row.to_dict() for row in bundle.rows]
    # Ingestion timestamps are audit metadata, not numerical model inputs. They
    # may be regenerated when an immutable fixture is parsed, so exclude them
    # from the reproducibility hash while retaining them in the returned rows.
    scientific_weather = [
        {key: value for key, value in row.items() if key != "ingested_at"}
        for row in weather
    ]
    run_inputs = {
        "pilot_id": pilot_id,
        "coordinates": pilot,
        "start": start,
        "end": end,
        "variables": WEATHER_VARIABLES,
        "weather": scientific_weather,
        "time_standards": bundle.time_standards,
    }
    return ServiceEnvelope(
        status=AnalysisStatus.OK,
        data={
            "pilot_id": pilot_id,
            "coordinates": pilot,
            "start": start,
            "end": end,
            "weather": weather,
            "coverage": coverage.data,
            "sources": bundle.source_ids,
            "time_standards": bundle.time_standards,
            "retrieval": result.retrieval,
        },
        model_run_id=model_run_id(
            inputs=run_inputs,
            evidence_ids=bundle.evidence_ids,
            model_versions={"earthsync": "1.0.0", "orbitill_weather_pipeline": "0.1.0"},
        ),
        evidence_ids=bundle.evidence_ids,
        is_synthetic=False,
        warnings=tuple(item.message for item in result.warnings),
        limitations=limitations,
    )
