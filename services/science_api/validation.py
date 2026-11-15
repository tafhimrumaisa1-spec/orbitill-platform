"""Cross-module validation at ORBITILL scientific service boundaries."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .contracts import AnalysisStatus, Insufficiency, ServiceEnvelope


@dataclass(frozen=True)
class WeatherCoverage:
    total_days: int
    usable_days: int
    fraction: float
    missing_fields: tuple[str, ...]


def validate_daily_weather(
    rows: Iterable[object],
    *,
    minimum_coverage: float = 0.90,
) -> ServiceEnvelope:
    """Require physically usable daily weather, beyond the presence of dates."""

    weather = list(rows)
    if not weather:
        return _weather_refusal("No daily weather rows were supplied.", ("daily_weather",))

    required = ("tmax_c", "tmin_c", "wind_2m_ms", "solar_mj_m2_day", "precip_mm")
    missing_fields: set[str] = set()
    usable = 0
    for row in weather:
        missing = [field for field in required if not _finite(getattr(row, field, None))]
        humidity_available = _finite(getattr(row, "tdew_c", None)) or _finite(
            getattr(row, "rh_mean_pct", None)
        )
        if not humidity_available:
            missing.append("tdew_c_or_rh_mean_pct")
        missing_fields.update(missing)
        if not missing:
            usable += 1

    fraction = usable / len(weather)
    coverage = WeatherCoverage(
        total_days=len(weather),
        usable_days=usable,
        fraction=fraction,
        missing_fields=tuple(sorted(missing_fields)),
    )
    if fraction < minimum_coverage:
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            data=coverage,
            insufficiencies=(
                Insufficiency(
                    code="insufficient_weather_coverage",
                    message=(
                        f"Only {usable} of {len(weather)} daily weather rows contain the "
                        "inputs needed for the water calculation."
                    ),
                    missing=coverage.missing_fields,
                    remedy="Retrieve the missing weather variables before calculating crop water demand.",
                ),
            ),
        )

    return ServiceEnvelope(status=AnalysisStatus.OK, data=coverage)


def validate_region_binding(*, farm_region_id: str, selected_region_id: str) -> ServiceEnvelope:
    if farm_region_id != selected_region_id:
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            insufficiencies=(
                Insufficiency(
                    code="region_mismatch",
                    message=(
                        f"Farm region {farm_region_id!r} cannot be evaluated with "
                        f"the {selected_region_id!r} rule pack."
                    ),
                    missing=("matching_region_profile",),
                    remedy="Select the farm's region profile or create a supported local profile.",
                ),
            ),
        )
    return ServiceEnvelope(status=AnalysisStatus.OK)


def validate_non_negative(value: float | None, *, field_name: str) -> ServiceEnvelope:
    if value is None:
        return ServiceEnvelope(
            status=AnalysisStatus.CONDITIONAL,
            insufficiencies=(
                Insufficiency(
                    code="missing_input",
                    message=f"{field_name} is unknown.",
                    missing=(field_name,),
                ),
            ),
        )
    if not _finite(value) or value < 0:
        return ServiceEnvelope(
            status=AnalysisStatus.REFUSED,
            insufficiencies=(
                Insufficiency(
                    code="invalid_input",
                    message=f"{field_name} must be a finite value greater than or equal to zero.",
                    missing=(field_name,),
                ),
            ),
        )
    return ServiceEnvelope(status=AnalysisStatus.OK, data=value)


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _weather_refusal(message: str, missing: tuple[str, ...]) -> ServiceEnvelope:
    return ServiceEnvelope(
        status=AnalysisStatus.REFUSED,
        insufficiencies=(
            Insufficiency(
                code="missing_weather",
                message=message,
                missing=missing,
                remedy="Retrieve a dated environmental series through EarthSync.",
            ),
        ),
    )
