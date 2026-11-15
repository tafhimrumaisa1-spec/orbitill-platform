"""Compare two climate series (e.g. POWER PRECTOTCORR vs IMERG) WITHOUT merging them.

Principles
----------
* Different measurement processes are different *views*, not replicates. We never average them.
  Output carries both totals and an ``envelope`` (min..max) so downstream scenario logic can treat the
  spread as uncertainty, and a ``disagreement_flags`` list with explicit, parameterised rules.
* Pair only days valid in BOTH series; report how many pairs survived.
* Footprint mismatch (e.g. 0.5x0.625 deg vs 0.1 deg) is flagged, never hidden or interpolated away.
* Day-boundary mismatch (UTC vs local solar day) is diagnosed with a +/-1 day lag check.
* Neither product is treated as truth: metrics are symmetric where possible (agreement, CSI), and
  bias is defined as mean(B - A) with A the first argument.
Thresholds for flags are descriptive heuristics (see ``DEFAULT_THRESHOLDS``), not validated skill limits.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from .cache import canonical_json
from .schemas import EnvironmentalSeries, Insufficiency, InsufficiencyCode, clean_floats

DEFAULT_THRESHOLDS = {
    "wet_day_mm": 1.0,
    "heavy_day_mm": 50.0,
    "total_ratio_range": (0.8, 1.25),
    "monthly_ratio_range": (0.67, 1.5),
    "monthly_min_total_mm": 20.0,
    "min_pearson": 0.5,
    "max_wet_freq_diff": 0.15,
    "lag_gain": 0.10,
    "footprint_area_ratio": 4.0,
    "min_overlap_days": 60,
    "min_pair_fraction": 0.80,
}


class DatasetComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0.0"
    comparison_id: str
    status: Literal["computed", "insufficient"]
    a_series_id: Optional[str] = None
    b_series_id: Optional[str] = None
    a_label: Optional[str] = None
    b_label: Optional[str] = None
    unit: Optional[str] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    n_overlap_days: int = 0
    n_valid_pairs: int = 0
    metrics: dict = Field(default_factory=dict)
    agreement: dict = Field(default_factory=dict)
    monthly: list[dict] = Field(default_factory=list)
    lag_check: dict = Field(default_factory=dict)
    heavy_rain: dict = Field(default_factory=dict)
    envelope_totals: dict = Field(default_factory=dict)
    disagreement_flags: list[str] = Field(default_factory=list)
    spatial_support: dict = Field(default_factory=dict)
    thresholds: dict = Field(default_factory=dict)
    recommended_use: str = "carry_both_as_range_do_not_average"
    caveats: list[str] = Field(default_factory=list)
    insufficiency: list[Insufficiency] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    is_synthetic: bool = False


def _rank(x: np.ndarray) -> np.ndarray:
    """Average ranks (ties share the mean rank)."""
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    sx = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _pearson(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _area_km2(s: EnvironmentalSeries) -> Optional[float]:
    sp = s.spatial
    return sp.footprint_km_ns * sp.footprint_km_ew if (sp.footprint_km_ns and sp.footprint_km_ew) else None


def _cid(a: EnvironmentalSeries, b: EnvironmentalSeries, start: str, end: str) -> str:
    return "cmp:" + hashlib.sha256(canonical_json([a.series_id, b.series_id, start, end]).encode()).hexdigest()[:12]


def _insufficient(cid: str, ins: Insufficiency, a: Optional[EnvironmentalSeries], b: Optional[EnvironmentalSeries], start=None, end=None) -> DatasetComparison:
    return DatasetComparison(comparison_id=cid, status="insufficient", a_series_id=a.series_id if a else None, b_series_id=b.series_id if b else None,
                             window_start=start, window_end=end, insufficiency=[ins], recommended_use="do_not_compare",
                             evidence_ids=sorted({s.evidence_id for s in (a, b) if s}), is_synthetic=any(s.is_synthetic for s in (a, b) if s))


def compare_series(a: Optional[EnvironmentalSeries], b: Optional[EnvironmentalSeries], *, start: Optional[str] = None, end: Optional[str] = None,
                   thresholds: Optional[dict] = None, missing_label: Optional[str] = None) -> DatasetComparison:
    th = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    if a is None or b is None:
        missing = [n for n, s in (("series_a", a), ("series_b", b)) if s is None]
        return _insufficient("cmp:missing", Insufficiency(
            code=InsufficiencyCode.missing_variable, message=f"Cannot compare: {missing_label or ', '.join(missing)} unavailable",
            missing=missing, remedy="Obtain the second dataset (see manifest access path) - the first dataset is NOT substituted for it."), a, b, start, end)
    s0 = max(start or a.dates[0], b.dates[0], a.dates[0])
    e0 = min(end or a.dates[-1], b.dates[-1], a.dates[-1])
    if start:
        s0 = max(s0, start)
    cid = _cid(a, b, s0, e0)
    if a.unit != b.unit:
        return _insufficient(cid, Insufficiency(code=InsufficiencyCode.unit_unrecognized, message=f"Units differ ({a.unit} vs {b.unit}); convert explicitly first"), a, b, s0, e0)
    if s0 > e0:
        return _insufficient(cid, Insufficiency(code=InsufficiencyCode.no_overlap, message="The two series do not overlap in time"), a, b, s0, e0)

    da = dict(zip(a.dates, a.values))
    db = dict(zip(b.dates, b.values))
    days = [(date.fromisoformat(s0) + timedelta(days=i)).isoformat() for i in range((date.fromisoformat(e0) - date.fromisoformat(s0)).days + 1)]
    pairs = [(d, da[d], db[d]) for d in days if da.get(d) is not None and db.get(d) is not None]
    n_over, n_pair = len(days), len(pairs)
    if n_pair < th["min_overlap_days"] or n_pair / max(n_over, 1) < th["min_pair_fraction"]:
        return _insufficient(cid, Insufficiency(
            code=InsufficiencyCode.insufficient_coverage,
            message=f"Only {n_pair} paired valid days out of {n_over} overlapping ({n_pair / max(n_over, 1):.0%}); need >= {th['min_overlap_days']} days and >= {th['min_pair_fraction']:.0%}",
            remedy="Widen the window or obtain gap-free extracts."), a, b, s0, e0)

    ds = [p[0] for p in pairs]
    x = np.array([p[1] for p in pairs], dtype=float)
    y = np.array([p[2] for p in pairs], dtype=float)
    diff = y - x
    metrics = {
        "mean_a": float(x.mean()), "mean_b": float(y.mean()), "total_a": float(x.sum()), "total_b": float(y.sum()),
        "bias_b_minus_a": float(diff.mean()), "ratio_b_over_a": float(y.sum() / x.sum()) if x.sum() > 0 else None,
        "rmse": float(np.sqrt((diff ** 2).mean())), "mae": float(np.abs(diff).mean()),
        "pearson_r": _pearson(x, y), "spearman_rho": _pearson(_rank(x), _rank(y)),
    }
    wet = th["wet_day_mm"]
    wa, wb = x >= wet, y >= wet
    both, only_a, only_b, neither = int((wa & wb).sum()), int((wa & ~wb).sum()), int((~wa & wb).sum()), int((~wa & ~wb).sum())
    union = both + only_a + only_b
    agreement = {"wet_day_threshold_mm": wet, "both_wet": both, "only_a_wet": only_a, "only_b_wet": only_b, "both_dry": neither,
                 "agreement_rate": (both + neither) / n_pair, "csi_symmetric": (both / union) if union else None,
                 "wet_freq_a": float(wa.mean()), "wet_freq_b": float(wb.mean())}
    # monthly totals
    monthly = []
    for m in sorted({d[:7] for d in ds}):
        idx = [i for i, d in enumerate(ds) if d[:7] == m]
        ta, tb = float(x[idx].sum()), float(y[idx].sum())
        monthly.append({"month": m, "n_days": len(idx), "total_a": ta, "total_b": tb, "ratio_b_over_a": (tb / ta) if ta > 0 else None})
    # lag check for UTC-vs-local-day offsets
    lag_corr = {}
    for k in (-1, 0, 1):
        xs, ys = [], []
        for d in ds:
            d2 = (date.fromisoformat(d) + timedelta(days=k)).isoformat()
            if d2 in db and db[d2] is not None:
                xs.append(da[d]); ys.append(db[d2])
        lag_corr[str(k)] = _pearson(np.array(xs), np.array(ys)) if len(xs) > 30 else None
    c0 = lag_corr["0"]
    best_k, best_c = "0", c0
    for k in ("-1", "1"):
        if lag_corr[k] is not None and (best_c is None or lag_corr[k] > best_c):
            best_k, best_c = k, lag_corr[k]
    lag = {"correlation_by_lag_days_b_shifted": lag_corr, "best_lag_days": int(best_k)}
    # heavy rain
    hv = th["heavy_day_mm"]
    ha, hb = x >= hv, y >= hv
    heavy = {"threshold_mm": hv, "days_a": int(ha.sum()), "days_b": int(hb.sum()), "days_both": int((ha & hb).sum()), "days_only_one": int((ha ^ hb).sum())}
    # flags
    flags: list[str] = []
    lo, hi = th["total_ratio_range"]
    r = metrics["ratio_b_over_a"]
    if r is not None and not (lo <= r <= hi):
        flags.append("total_ratio_outside_range")
    mlo, mhi = th["monthly_ratio_range"]
    if any(m["ratio_b_over_a"] is not None and m["total_a"] >= th["monthly_min_total_mm"] and not (mlo <= m["ratio_b_over_a"] <= mhi) for m in monthly):
        flags.append("monthly_ratio_outside_range")
    if metrics["pearson_r"] is not None and metrics["pearson_r"] < th["min_pearson"]:
        flags.append("low_daily_correlation")
    if abs(agreement["wet_freq_a"] - agreement["wet_freq_b"]) > th["max_wet_freq_diff"]:
        flags.append("wet_day_frequency_differs")
    if best_k != "0" and c0 is not None and best_c - c0 >= th["lag_gain"]:
        flags.append("possible_day_boundary_offset")
    if heavy["days_only_one"] > 0:
        flags.append("heavy_rain_disagreement")
    aa, ab = _area_km2(a), _area_km2(b)
    sp = {"a_footprint_km2": aa, "b_footprint_km2": ab, "a_cell": a.spatial.cell_id, "b_cell": b.spatial.cell_id}
    if aa and ab and max(aa, ab) / min(aa, ab) > th["footprint_area_ratio"]:
        flags.append("spatial_support_mismatch")
        sp["note"] = f"Footprints differ by {max(aa, ab) / min(aa, ab):.0f}x: differences partly reflect spatial scale, not only measurement error."
    caveats = [
        "The products are different measurement processes; they are reported side by side and never averaged.",
        "Neither product is ground truth. PRECTOTCORR is observation-corrected reanalysis; IMERG is a satellite estimate (Final Run gauge-calibrated), so they may share gauge information and are not fully independent.",
        "Flag thresholds are descriptive heuristics, not validated skill limits.",
    ]
    if a.is_synthetic or b.is_synthetic:
        caveats.append("SYNTHETIC DEMONSTRATION DATA involved - comparison is illustrative only.")
    return DatasetComparison(
        comparison_id=cid, status="computed", a_series_id=a.series_id, b_series_id=b.series_id,
        a_label=f"{a.source_id}:{a.provider_variable}", b_label=f"{b.source_id}:{b.provider_variable}", unit=a.unit, window_start=s0, window_end=e0,
        n_overlap_days=n_over, n_valid_pairs=n_pair, metrics=clean_floats(metrics), agreement=clean_floats(agreement), monthly=clean_floats(monthly),
        lag_check=clean_floats(lag), heavy_rain=heavy,
        envelope_totals={"total_min": float(min(x.sum(), y.sum())), "total_max": float(max(x.sum(), y.sum())), "unit": a.unit, "basis": "paired valid days only"},
        disagreement_flags=flags, spatial_support=clean_floats(sp), thresholds={k: (list(v) if isinstance(v, tuple) else v) for k, v in th.items()},
        caveats=caveats, evidence_ids=sorted({a.evidence_id, b.evidence_id}), is_synthetic=a.is_synthetic or b.is_synthetic)
