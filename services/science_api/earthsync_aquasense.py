"""Lossless boundary adapter from EarthSync observations to AquaSense weather.

The source modules remain authoritative. This adapter translates field names and
propagates provenance so normalized EarthSync records are not silently dropped by
AquaSense's provider-variable interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class WeatherBundle:
    """AquaSense-ready weather plus the lineage needed by result envelopes."""

    rows: tuple[object, ...]
    evidence_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    time_standards: tuple[str, ...]
    is_synthetic: bool


def earthsync_observations_to_aquasense(observations: Iterable[object]) -> list[object]:
    """Convert EarthSync Observation objects into AquaSense DailyWeather rows.

    Imports stay inside the function so this module can be inspected without
    installing either agent package. Both packages must be on ``PYTHONPATH`` when
    the adapter runs.
    """

    from aquasense.models import Observation as AquaObservation
    from aquasense.power_adapter import observations_to_weather

    converted = []
    for observation in observations:
        spatial = observation.spatial
        bbox = getattr(spatial, "footprint_bbox_wsen", None)
        latitude = None
        longitude = None
        if bbox and len(bbox) == 4:
            longitude = (bbox[0] + bbox[2]) / 2
            latitude = (bbox[1] + bbox[3]) / 2

        converted.append(
            AquaObservation(
                source_id=observation.source_id,
                variable=observation.provider_variable,
                value=observation.value,
                unit=observation.unit,
                observed_on=date.fromisoformat(observation.observation_time[:10]),
                lat=latitude,
                lon=longitude,
                source_version=observation.source_version or "",
                ingested_at=observation.ingestion_time or "",
                native_resolution=_spatial_label(spatial),
                quality_flags=tuple(observation.quality_flags),
                data_type=(
                    "hypothetical_scenario"
                    if observation.is_synthetic
                    else observation.data_type
                ),
            )
        )

    return observations_to_weather(converted)


def earthsync_series_to_weather_bundle(series_objects: Iterable[object]) -> WeatherBundle:
    """Translate EarthSync series without discarding their shared provenance.

    Time standards live on EarthSync series rather than individual observations,
    so callers should prefer this boundary over flattening observations manually.
    """

    series = list(series_objects)
    observations = [observation for item in series for observation in item.observations()]
    return WeatherBundle(
        rows=tuple(earthsync_observations_to_aquasense(observations)),
        evidence_ids=tuple(sorted({item.evidence_id for item in series})),
        source_ids=tuple(sorted({item.source_id for item in series})),
        time_standards=tuple(sorted({item.temporal.time_standard for item in series})),
        is_synthetic=any(item.is_synthetic for item in series),
    )


def _spatial_label(spatial: object) -> str:
    parts = []
    lat_deg = getattr(spatial, "native_resolution_lat_deg", None)
    lon_deg = getattr(spatial, "native_resolution_lon_deg", None)
    resolution_m = getattr(spatial, "native_resolution_m", None)
    if lat_deg is not None and lon_deg is not None:
        parts.append(f"{lat_deg:g}x{lon_deg:g} deg")
    if resolution_m is not None:
        parts.append(f"{resolution_m:g} m")
    note = getattr(spatial, "note", None)
    if note:
        parts.append(str(note))
    return " · ".join(parts) or "spatial support supplied by EarthSync"

