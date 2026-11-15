"""GPM IMERG rainfall: unit-safe ingest for daily extracts + half-hourly aggregation.

Live Earthdata access is NOT implemented (credentials + network required); the supported routes are
  (a) POWER-hosted IMERG parameter (see variables.POWER_IMERG_PARAM_CANDIDATES; unverified code), and
  (b) a user-downloaded daily time-series extract (Giovanni / GES DISC / AppEEARS CSV) with declared metadata.

IMERG facts used (GPM IMERG V07 documentation): 0.1 x 0.1 deg grid, 30-min rate in mm/hr,
runs Early (~4 h), Late (~12 h), Final (~3.5 months, gauge-calibrated). Fill value -9999.9 in rate fields.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional

from .. import gridinfo as G
from ..schemas import EnvironmentalSeries, EvidenceRecord, LicenseInfo
from ..units import rate_to_depth
from .reference_csv import ExtractSpec, load_series_csv

RUNS = ("Early", "Late", "Final")
IMERG_LICENSE = LicenseInfo(name="NASA Earth science open data policy", url="https://gpm.nasa.gov/data/imerg",
                            attribution="Huffman, G.J., et al., GPM IMERG; NASA GES DISC", verified=False,
                            note="Not read in this build; confirm citation/DOI for the exact version and run.")


def daily_from_halfhourly(timestamps_utc: Iterable[str], rates_mm_per_hr: Iterable[Optional[float]], *, min_valid_halfhours: int = 44) -> dict[str, Optional[float]]:
    """Daily accumulation (mm) from 30-min *rates* (mm/hr): sum(rate * 0.5 h). UTC days (IMERG time is UTC).

    Days with fewer than ``min_valid_halfhours`` of 48 valid slots return None (not a partial sum).
    Fill (<0) values are invalid.
    """
    acc: dict[str, list[float]] = defaultdict(list)
    for ts, r in zip(timestamps_utc, rates_mm_per_hr):
        day = ts[:10]
        if r is not None and r >= 0:
            acc[day].append(rate_to_depth(float(r), 0.5))
        else:
            acc.setdefault(day, [])
    return {d: (round(sum(v), 4) if len(v) >= min_valid_halfhours else None) for d, v in sorted(acc.items())}


def load_imerg_daily_csv(source: str | Path, *, run: str, version: str, lat: float, lon: float, declared_unit: str, date_col: str, value_col: str,
                         area_mean_over_footprint: bool, downloaded_at_utc: Optional[str] = None, original_url: Optional[str] = None
                         ) -> tuple[EnvironmentalSeries, EvidenceRecord]:
    """Ingest a daily IMERG extract. ``declared_unit`` must be 'mm/day' (accumulation); mm/hr is rejected here
    because a daily *rate* field must be converted explicitly by the caller (x24), not guessed."""
    if run not in RUNS:
        raise ValueError(f"run must be one of {RUNS}")
    spatial = G.spatial_support_for(lat, lon, G.IMERG_01, note=("Area mean over the user-declared footprint." if area_mean_over_footprint
                                                                 else "Value of the single 0.1 deg IMERG cell containing the point."))
    spec = ExtractSpec(
        source_id="NASA_GPM_IMERG", provider="NASA GES DISC / GPM", dataset_name=f"GPM IMERG {run} Run daily precipitation", dataset_version=f"V{version}",
        variable="precipitation_imerg", provider_variable=f"IMERG_{run.upper()}", dimension="precip_depth", declared_unit=declared_unit, date_col=date_col,
        value_col=value_col, spatial=spatial, data_type="observed", measurement_process="satellite_retrieval", license=IMERG_LICENSE,
        citation="Huffman et al., GPM IMERG (cite exact version/DOI at https://gpm.nasa.gov/data/imerg)", original_url=original_url, downloaded_at_utc=downloaded_at_utc,
        fill_values=(-9999.9, -9999.0, -999.0), lo=0.0, hi=1500.0, time_standard="UTC",
        day_boundary_note="IMERG days are UTC (00-24 UTC). Bangladesh local day (UTC+6) is offset by 6 h; compare with POWER day-by-day only after a lag check.",
        extra_caveats=[f"IMERG {run} Run: " + ("gauge-calibrated, months latency." if run == "Final" else "near-real-time, not gauge-calibrated."),
                       "Satellite precipitation estimate, not a rain gauge."])
    return load_series_csv(source, spec)
