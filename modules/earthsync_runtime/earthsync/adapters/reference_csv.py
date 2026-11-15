"""Declared-metadata CSV ingest for provider extracts the user downloaded themselves.

Used for IMERG/Giovanni exports, PRISM point time series, CoCoRaHS station CSVs, etc., where
there is no live adapter. The caller MUST declare unit, dimension, provenance and footprint:
we refuse to guess units or spatial support from column names.
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..cache import utcnow_iso
from ..errors import SourceError
from ..schemas import (EnvironmentalSeries, EvidenceRecord, Insufficiency, InsufficiencyCode, LicenseInfo, SpatialSupport,
                       TemporalSupport, TransformationStep)
from ..units import CANON, UnitError, to_canonical


@dataclass
class ExtractSpec:
    source_id: str
    provider: str
    dataset_name: str
    dataset_version: str
    variable: str
    provider_variable: str
    dimension: str                 # key into units.CANON
    declared_unit: str             # e.g. 'mm/day', 'degC'
    date_col: str
    value_col: str
    spatial: SpatialSupport
    data_type: str                 # observed | model_estimate | ...
    measurement_process: str
    license: LicenseInfo
    citation: str
    original_url: Optional[str] = None
    downloaded_at_utc: Optional[str] = None   # when the user downloaded it (declared)
    fill_values: tuple[float, ...] = (-9999.0, -999.0, -9999.9)
    lo: float = -1e9
    hi: float = 1e9
    time_standard: str = "provider_default"
    day_boundary_note: Optional[str] = None
    extra_caveats: list[str] = field(default_factory=list)
    date_format: str = "%Y-%m-%d"


def load_series_csv(source: str | Path, spec: ExtractSpec) -> tuple[EnvironmentalSeries, EvidenceRecord]:
    text = Path(source).read_text(encoding="utf-8") if not (isinstance(source, str) and "\n" in source) else source
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if spec.date_col in ln.split(",")[0] or spec.date_col in ln), None)
    if start is None:
        raise SourceError(Insufficiency(code=InsufficiencyCode.invalid_response, message=f"Header with column {spec.date_col!r} not found in extract"))
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    if spec.value_col not in (reader.fieldnames or []):
        raise SourceError(Insufficiency(code=InsufficiencyCode.invalid_response,
                                        message=f"Column {spec.value_col!r} not in extract columns {reader.fieldnames}"))
    dates, vals, flags = [], [], {}
    for row in reader:
        raw_d = (row.get(spec.date_col) or "").strip()
        if not raw_d:
            continue
        try:
            d = datetime.strptime(raw_d[:len(datetime.now().strftime(spec.date_format))], spec.date_format).date().isoformat()
        except ValueError:
            raise SourceError(Insufficiency(code=InsufficiencyCode.invalid_response, message=f"Unparseable date {raw_d!r} (format {spec.date_format})"))
        raw_v = (row.get(spec.value_col) or "").strip()
        dates.append(d)
        try:
            fv = float(raw_v)
        except ValueError:
            vals.append(None); flags[d] = ["missing"]; continue
        if fv in spec.fill_values:
            vals.append(None); flags[d] = ["fill_value"]; continue
        try:
            cv, _, conv = to_canonical(fv, spec.declared_unit, spec.dimension)
        except UnitError as ue:
            raise SourceError(ue.to_insufficiency()) from ue
        if not (spec.lo <= cv <= spec.hi):
            vals.append(None); flags[d] = ["rejected_out_of_range"]; continue
        vals.append(round(cv, 4))
        if conv:
            flags[d] = ["unit_converted"]
    if not dates:
        raise SourceError(Insufficiency(code=InsufficiencyCode.invalid_response, message="Extract contains no data rows"))
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    ev_id = f"ev:{spec.source_id.lower()}:{sha[:12]}"
    temporal = TemporalSupport(step="daily", time_standard=spec.time_standard, start=dates[0], end=dates[-1], day_boundary_note=spec.day_boundary_note)
    ev = EvidenceRecord(
        evidence_id=ev_id, source_id=spec.source_id, provider=spec.provider, dataset_name=spec.dataset_name, dataset_version=spec.dataset_version,
        original_url=spec.original_url, citation=spec.citation, retrieved_at_utc=spec.downloaded_at_utc or utcnow_iso(), retrieval_mode="user_supplied_extract",
        spatial=spec.spatial, temporal=temporal, variables=[spec.provider_variable],
        transformations=[TransformationStep(step_id="ing", name="declared_metadata_csv_ingest",
                                            params={"declared_unit": spec.declared_unit, "value_col": spec.value_col, "fill_values": list(spec.fill_values)},
                                            description="Unit and footprint are caller-declared, not inferred from the file.")],
        license=spec.license, payload_sha256=sha, adapter_version="earthsync-reference-csv/0.1.0",
        caveats=["User-supplied extract: provenance beyond the declared metadata cannot be verified by EarthSync."] + spec.extra_caveats)
    ser = EnvironmentalSeries(
        series_id=f"ser:{spec.source_id.lower()}:{spec.provider_variable}:{dates[0]}..{dates[-1]}:{sha[:8]}", source_id=spec.source_id, source_version=spec.dataset_version,
        variable=spec.variable, provider_variable=spec.provider_variable, unit=CANON[spec.dimension], dates=dates, values=vals, flags=flags, spatial=spec.spatial,
        temporal=temporal, data_type=spec.data_type, measurement_process=spec.measurement_process, evidence_id=ev_id,
        retrieval_mode="user_supplied_extract", ingestion_time=utcnow_iso(), caveats=list(ev.caveats))
    return ser, ev
