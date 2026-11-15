"""Canonical integration records shared by ORBITILL service adapters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AnalysisStatus(str, Enum):
    OK = "ok"
    CONDITIONAL = "conditional"
    WATER_CONSTRAINED = "water_constrained"
    INFEASIBLE = "infeasible"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class Readiness(str, Enum):
    EXPLORATION = "exploration"
    CONDITIONAL = "conditional"
    RESEARCH_PILOT = "research_pilot"
    VALIDATED_WITH_EVIDENCE = "validated_with_evidence"


class DataType(str, Enum):
    OBSERVED = "observed"
    REANALYSIS = "reanalysis"
    FARMER_REPORTED = "farmer_reported"
    GROUND_MEASURED = "ground_measured"
    PUBLISHED_REFERENCE = "published_reference"
    MODEL_ESTIMATE = "model_estimate"
    FORECAST = "forecast"
    CLIMATE_PROJECTION = "climate_projection"
    HYPOTHETICAL_SCENARIO = "hypothetical_scenario"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


@dataclass(frozen=True)
class Insufficiency:
    code: str
    message: str
    missing: tuple[str, ...] = ()
    remedy: str | None = None
    severity: str = "blocking"


@dataclass(frozen=True)
class ServiceEnvelope:
    status: AnalysisStatus
    data: Any = None
    insufficiencies: tuple[Insufficiency, ...] = ()
    warnings: tuple[str, ...] = ()
    model_run_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    is_synthetic: bool = False
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


def model_run_id(
    *,
    inputs: Any,
    evidence_ids: list[str] | tuple[str, ...],
    model_versions: dict[str, str],
) -> str:
    """Hash exact model inputs, evidence identities, and implementation versions."""

    payload = {
        "inputs": inputs,
        "evidence_ids": sorted(evidence_ids),
        "model_versions": dict(sorted(model_versions.items())),
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"run_{digest[:20]}"


def _canonical_json(value: Any) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
