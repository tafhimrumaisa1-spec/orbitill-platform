"""Physically meaningful features from NASA-centric series, with coverage gating.

Every function returns a ``Feature``. A feature is one of:
  computed     - enough valid days; value is the honest statistic of what was observed
  bounded      - some days missing; only a one-sided bound is mathematically defensible
  insufficient - not enough valid data (or a required variable missing); ``value`` is None
                 and ``insufficiency`` explains why. Nothing is imputed, ever.

Windows are calendar windows in ISO dates. Days absent from a series count as missing.
Crop thresholds are *arguments* (owned by SoilBrain); this module hard-codes no crop rule.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Callable, Optional, Sequence

import numpy as np

from . import et0 as ET0
from .cache import canonical_json
from .schemas import (Coverage, EnvironmentalSeries, EvidenceRecord, Feature, Insufficiency, InsufficiencyCode,
                      SpatialSupport, TemporalSupport, TransformationStep, LicenseInfo)

METHOD_VERSION = "1"
DEFAULT_MIN_COVERAGE = 0.90


# ----------------------------------------------------------------- helpers
def _daterange(start: str, end: str) -> list[str]:
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    return [(s + timedelta(days=i)).isoformat() for i in range((e - s).days + 1)]


def window_array(series: EnvironmentalSeries, start: str, end: str) -> np.ndarray:
    """Full calendar window; NaN where missing OR absent from the stored series."""
    lookup = {d: v for d, v in zip(series.dates, series.values)}
    return np.array([np.nan if lookup.get(d) is None else float(lookup[d]) for d in _daterange(start, end)], dtype=float)


def _coverage(arr: np.ndarray) -> Coverage:
    expected, valid = len(arr), int(np.isfinite(arr).sum())
    return Coverage(expected_days=expected, valid_days=valid, missing_days=expected - valid, fraction=(valid / expected) if expected else 0.0)


def _fid(method: str, series_ids: Sequence[str], start: str, end: str, params: dict) -> str:
    h = hashlib.sha256(canonical_json({"s": list(series_ids), "w": [start, end], "p": params}).encode()).hexdigest()[:10]
    return f"feat:{method}:{h}"


def _base(series_list: Sequence[EnvironmentalSeries]) -> dict:
    syn = any(s.is_synthetic for s in series_list)
    s0 = series_list[0]
    sp = s0.spatial
    note = None
    if sp.footprint_km_ns:
        note = "; ".join(sorted({f"{s.provider_variable}: {s.spatial.footprint_km_ns:.0f}x{s.spatial.footprint_km_ew:.0f} km cell" for s in series_list if s.spatial.footprint_km_ns}))
    return dict(
        input_series_ids=[s.series_id for s in series_list],
        evidence_ids=sorted({s.evidence_id for s in series_list}),
        data_type="hypothetical_scenario" if syn else "model_estimate",
        is_synthetic=syn,
        spatial_note=(note + ". Applies to the grid cell, not an individual field.") if note else None,
        caveats=(["SYNTHETIC DEMONSTRATION DATA - result is illustrative only."] if syn else []),
    )


def _insufficient(*, feature_id, name, family, unit, start, end, method_id, params, series_list, ins: list[Insufficiency], cov: Optional[Coverage] = None) -> Feature:
    b = _base(series_list) if series_list else dict(input_series_ids=[], evidence_ids=[], data_type="model_estimate", is_synthetic=False, spatial_note=None, caveats=[])
    return Feature(feature_id=feature_id, name=name, family=family, status="insufficient", value=None, unit=unit, window_start=start, window_end=end,
                   method_id=method_id, method_params=params, coverage=cov, insufficiency=ins, **b)


def missing_variable(name: str, required_by: str) -> Insufficiency:
    return Insufficiency(code=InsufficiencyCode.missing_variable, message=f"Required variable {name} is not available",
                         missing=[name], required_by=required_by,
                         remedy="Fetch the variable from its registered source (see source manifest) or supply a farmer/local measurement; no value was assumed.")


def _gate(arrays: Sequence[np.ndarray], min_cov: float) -> tuple[Coverage, Optional[Insufficiency]]:
    both = np.all([np.isfinite(a) for a in arrays], axis=0) if arrays else np.array([])
    cov = _coverage(np.where(both, 1.0, np.nan))
    if cov.fraction < min_cov:
        return cov, Insufficiency(code=InsufficiencyCode.insufficient_coverage,
                                  message=f"Only {cov.valid_days}/{cov.expected_days} valid days ({cov.fraction:.0%}) in window; need >= {min_cov:.0%}",
                                  remedy="Extend the data range, fix the gap at the source, or report the question as unanswered.")
    return cov, None


# ----------------------------------------------------------------- features
def window_total(series: Optional[EnvironmentalSeries], start: str, end: str, *, name: str, family: str = "water_input",
                 min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    mid = "window_total"
    params = {"min_coverage": min_coverage}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], start, end, params)
    if series is None:
        return _insufficient(feature_id=fid, name=name, family=family, unit="", start=start, end=end, method_id=mid, params=params,
                             series_list=[], ins=[missing_variable("series", name)])
    arr = window_array(series, start, end)
    cov, ins = _gate([arr], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family=family, unit=series.unit, start=start, end=end, method_id=mid, params=params,
                             series_list=[series], ins=[ins], cov=cov)
    total = float(np.nansum(arr))
    base = _base([series])
    if cov.missing_days:
        base["caveats"] = base["caveats"] + [f"{cov.missing_days} missing day(s): total is a lower bound (missing days contributed 0 and were NOT imputed)."]
        return Feature(feature_id=fid, name=name, family=family, status="bounded", value=total, value_lower=total, unit=series.unit, window_start=start,
                       window_end=end, method_id=mid, method_params=params, coverage=cov, **base)
    return Feature(feature_id=fid, name=name, family=family, status="computed", value=total, unit=series.unit, window_start=start, window_end=end,
                   method_id=mid, method_params=params, coverage=cov, **base)


def window_mean(series: Optional[EnvironmentalSeries], start: str, end: str, *, name: str, family: str = "other",
                min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    mid = "window_mean"
    params = {"min_coverage": min_coverage}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], start, end, params)
    if series is None:
        return _insufficient(feature_id=fid, name=name, family=family, unit="", start=start, end=end, method_id=mid, params=params,
                             series_list=[], ins=[missing_variable("series", name)])
    arr = window_array(series, start, end)
    cov, ins = _gate([arr], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family=family, unit=series.unit, start=start, end=end, method_id=mid, params=params,
                             series_list=[series], ins=[ins], cov=cov)
    return Feature(feature_id=fid, name=name, family=family, status="computed", value=float(np.nanmean(arr)), unit=series.unit,
                   window_start=start, window_end=end, method_id=mid, method_params=params, coverage=cov, **_base([series]))


_OPS: dict[str, Callable] = {">=": np.greater_equal, ">": np.greater, "<=": np.less_equal, "<": np.less}


def count_days(series: Optional[EnvironmentalSeries], start: str, end: str, *, op: str, threshold: float, name: str, family: str = "heat",
               min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    """Number of days with value <op> threshold (e.g. Tmax >= 35 degC). Missing days make this a lower bound."""
    mid = "count_days"
    params = {"op": op, "threshold": threshold, "min_coverage": min_coverage}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], start, end, params)
    if op not in _OPS:
        raise ValueError(f"op must be one of {list(_OPS)}")
    if series is None:
        return _insufficient(feature_id=fid, name=name, family=family, unit="days", start=start, end=end, method_id=mid, params=params,
                             series_list=[], ins=[missing_variable("series", name)])
    arr = window_array(series, start, end)
    cov, ins = _gate([arr], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family=family, unit="days", start=start, end=end, method_id=mid, params=params,
                             series_list=[series], ins=[ins], cov=cov)
    hit = int(np.sum(_OPS[op](arr[np.isfinite(arr)], threshold)))
    base = _base([series])
    if cov.missing_days:
        return Feature(feature_id=fid, name=name, family=family, status="bounded", value=float(hit), value_lower=float(hit), value_upper=float(hit + cov.missing_days),
                       unit="days", window_start=start, window_end=end, method_id=mid, method_params=params, coverage=cov,
                       **{**base, "caveats": base["caveats"] + [f"{cov.missing_days} missing day(s): true count lies in [{hit}, {hit + cov.missing_days}]."]})
    return Feature(feature_id=fid, name=name, family=family, status="computed", value=float(hit), unit="days", window_start=start, window_end=end,
                   method_id=mid, method_params=params, coverage=cov, **base)


def longest_spell(series: Optional[EnvironmentalSeries], start: str, end: str, *, below: float, name: str, family: str = "water_input",
                  min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    """Longest run of consecutive days with value < ``below`` (dry spell for rain < threshold).

    Missing days are UNKNOWN, so the answer is an interval: lower = longest run of *known* dry days,
    upper = longest run if every missing day were dry. When nothing is missing lower == upper.
    """
    mid = "longest_spell_below"
    params = {"below": below, "min_coverage": min_coverage}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], start, end, params)
    if series is None:
        return _insufficient(feature_id=fid, name=name, family=family, unit="days", start=start, end=end, method_id=mid, params=params,
                             series_list=[], ins=[missing_variable("series", name)])
    arr = window_array(series, start, end)
    cov, ins = _gate([arr], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family=family, unit="days", start=start, end=end, method_id=mid, params=params,
                             series_list=[series], ins=[ins], cov=cov)

    def longest(mask: np.ndarray) -> int:
        best = cur = 0
        for m in mask:
            cur = cur + 1 if m else 0
            best = max(best, cur)
        return best

    known_dry = np.isfinite(arr) & (arr < below)
    maybe_dry = known_dry | ~np.isfinite(arr)
    lo, hi = longest(known_dry), longest(maybe_dry)
    base = _base([series])
    status = "computed" if lo == hi else "bounded"
    caveats = base["caveats"] + ([] if lo == hi else [f"Missing days make the longest spell lie in [{lo}, {hi}] days."])
    return Feature(feature_id=fid, name=name, family=family, status=status, value=float(lo), value_lower=float(lo), value_upper=float(hi), unit="days",
                   window_start=start, window_end=end, method_id=mid, method_params=params, coverage=cov, **{**base, "caveats": caveats})


def growing_degree_days(tmax: Optional[EnvironmentalSeries], tmin: Optional[EnvironmentalSeries], start: str, end: str, *, base_c: float,
                        cap_c: Optional[float] = None, name: str = "Growing degree days", min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    """GDD (degC-day). Daily Tmax and Tmin are clipped to [base, cap] before averaging (McMaster & Wilhelm 1997, method 'clip both').

    ``base_c``/``cap_c`` are crop parameters supplied by the caller (SoilBrain); none are defaulted here.
    """
    mid = "gdd_clipped"
    params = {"base_c": base_c, "cap_c": cap_c, "min_coverage": min_coverage}
    sl = [s for s in (tmax, tmin) if s is not None]
    fid = _fid(mid, [s.series_id for s in sl] or ["<missing>"], start, end, params)
    miss = [n for n, s in (("T2M_MAX", tmax), ("T2M_MIN", tmin)) if s is None]
    if miss:
        return _insufficient(feature_id=fid, name=name, family="heat", unit="degC-day", start=start, end=end, method_id=mid, params=params, series_list=sl,
                             ins=[missing_variable(m, name) for m in miss])
    a, b = window_array(tmax, start, end), window_array(tmin, start, end)
    cov, ins = _gate([a, b], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family="heat", unit="degC-day", start=start, end=end, method_id=mid, params=params, series_list=sl, ins=[ins], cov=cov)
    ok = np.isfinite(a) & np.isfinite(b)
    hi = a[ok] if cap_c is None else np.minimum(a[ok], cap_c)
    lo = np.maximum(b[ok], base_c)
    hi = np.maximum(hi, base_c)
    lo = lo if cap_c is None else np.minimum(lo, cap_c)
    gdd = float(np.sum((hi + lo) / 2.0 - base_c))
    base = _base(sl)
    status = "computed" if cov.missing_days == 0 else "bounded"
    caveats = base["caveats"] + ([] if status == "computed" else [f"{cov.missing_days} day(s) missing: GDD is a lower bound."])
    return Feature(feature_id=fid, name=name, family="heat", status=status, value=gdd, value_lower=gdd if status == "bounded" else None, unit="degC-day",
                   window_start=start, window_end=end, method_id=mid, method_params=params, coverage=cov, **{**base, "caveats": caveats})


def dekadal_totals(series: Optional[EnvironmentalSeries], start: str, end: str, *, name: str = "Dekadal totals", min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    """Totals per FAO dekad (days 1-10, 11-20, 21-end of month). Each dekad is gated separately; weak dekads are null."""
    mid = "dekadal_totals"
    params = {"min_coverage": min_coverage}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], start, end, params)
    if series is None:
        return _insufficient(feature_id=fid, name=name, family="water_input", unit="", start=start, end=end, method_id=mid, params=params, series_list=[], ins=[missing_variable("series", name)])
    days = _daterange(start, end)
    arr = window_array(series, start, end)
    dek: dict[str, list[float]] = {}
    for d, v in zip(days, arr):
        dd = int(d[8:10])
        k = f"{d[:7]}-D{1 if dd <= 10 else 2 if dd <= 20 else 3}"
        dek.setdefault(k, []).append(v)
    out = []
    for k, vs in dek.items():
        a = np.array(vs)
        frac = float(np.isfinite(a).mean())
        out.append({"dekad": k, "total": float(np.nansum(a)) if frac >= min_coverage else None, "valid_fraction": round(frac, 3), "days": len(a)})
    cov = _coverage(arr)
    ok_total = [o["total"] for o in out if o["total"] is not None]
    return Feature(feature_id=fid, name=name, family="water_input", status="computed" if len(ok_total) == len(out) else "bounded",
                   value=float(sum(ok_total)) if ok_total else None, unit=series.unit, window_start=start, window_end=end, method_id=mid, method_params=params,
                   coverage=cov, detail={"dekads": out}, **_base([series]))


# ------------------------------------------------------- ET0 and water balance
def derive_et0_series(series: dict[str, EnvironmentalSeries], *, lat: float, start: str, end: str, elevation_m: Optional[float] = None,
                      ) -> tuple[Optional[EnvironmentalSeries], Optional[EvidenceRecord], list[Insufficiency]]:
    """Build a daily FAO-56 ET0 series from POWER series. Needs T2M_MAX, T2M_MIN, ALLSKY_SFC_SW_DWN, WS2M and (T2MDEW or RH2M).

    Returns (series, derived EvidenceRecord, insufficiencies). If a required input is missing the series is None
    and the insufficiency names exactly what is missing.
    """
    need = ["T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "WS2M"]
    miss = [n for n in need if n not in series]
    if "T2MDEW" not in series and "RH2M" not in series:
        miss.append("T2MDEW|RH2M")
    if miss:
        return None, None, [missing_variable(m, "reference_et0_fao56") for m in miss]
    days = _daterange(start, end)
    arrs = {k: window_array(series[k], start, end) for k in series}
    tdew = arrs.get("T2MDEW")
    rh = arrs.get("RH2M")
    doy = np.array([date.fromisoformat(d).timetuple().tm_yday for d in days])
    ps = arrs.get("PS")
    if ps is not None and np.isfinite(ps).any():
        p_kpa = ps
        z = elevation_m
        z_src = "given" if elevation_m is not None else "inferred_from_PS"
    elif elevation_m is not None:
        p_kpa, z, z_src = None, elevation_m, "given"
    else:
        return None, None, [Insufficiency(code=InsufficiencyCode.missing_variable, message="Need elevation_m or PS to compute the psychrometric constant",
                                          missing=["elevation_m|PS"], required_by="reference_et0_fao56")]
    if z is None:
        z = float(np.nanmean(ET0.elevation_from_pressure(p_kpa)))
    et, parts = ET0.et0_pm_daily(arrs["T2M_MAX"], arrs["T2M_MIN"], arrs["ALLSKY_SFC_SW_DWN"], arrs["WS2M"], lat, doy, elevation_m=z, pressure_kpa=p_kpa,
                                 tdew=tdew if "T2MDEW" in series else None, rh_mean=rh if "T2MDEW" not in series else None, return_parts=True)
    hum = "T2MDEW" if "T2MDEW" in series else "RH2M"   # only the humidity route actually used is lineage
    inputs = [series[k] for k in need + [hum] + (["PS"] if p_kpa is not None else [])]
    syn = any(s.is_synthetic for s in inputs)
    h = hashlib.sha256(canonical_json([s.series_id for s in inputs] + [start, end, lat]).encode()).hexdigest()[:12]
    ev_id, ser_id = f"ev:derived:et0:{h}", f"ser:derived:ET0_FAO56:{start}..{end}:{h[:8]}"
    ref = series["T2M_MAX"]
    ev = EvidenceRecord(
        evidence_id=ev_id, source_id="NASA_POWER", provider="EarthSync derivation from NASA POWER inputs", dataset_name="FAO-56 Penman-Monteith ET0 (derived)",
        dataset_version="earthsync-et0/1", original_url=None, citation="Allen et al. (1998) FAO Irrigation and Drainage Paper 56, Eq. 6",
        retrieved_at_utc=None, retrieval_mode=ref.retrieval_mode, spatial=ref.spatial, temporal=TemporalSupport(step="daily", start=start, end=end),
        variables=["reference_et0_fao56"],
        transformations=[TransformationStep(step_id="et0", name="fao56_penman_monteith_daily", version="1",
                                            params={"latitude": lat, "elevation_m": round(float(z), 1), "elevation_source": z_src, "humidity_route": parts["ea_route"],
                                                    "albedo": ET0.ALBEDO, "G": 0.0, "inputs": [s.provider_variable for s in inputs]},
                                            description="Tmean=(Tmax+Tmin)/2; G=0; Rs/Rso clipped to [0.3,1]; wind at 2 m (POWER WS2M)")],
        license=LicenseInfo(name="CC BY 4.0 (inputs)", url="https://power.larc.nasa.gov/docs/referencing/", verified=True),
        is_synthetic=syn, adapter_version="earthsync-et0/0.1.0",
        caveats=["ET0 is atmospheric evaporative demand of a reference grass surface computed from ~55x63 km gridded forcing; not crop water use, not measured.",
                 "Flooded paddy and upland crops need different water-balance treatment (AquaSense)."] + (["SYNTHETIC inputs"] if syn else []),
        extras={"input_series_ids": [s.series_id for s in inputs], "input_evidence_ids": sorted({s.evidence_id for s in inputs})})
    vals = [None if not np.isfinite(v) else round(float(v), 3) for v in et]
    out = EnvironmentalSeries(series_id=ser_id, source_id="NASA_POWER", source_version="derived:earthsync-et0/1", variable="reference_et0_fao56", provider_variable="ET0_FAO56",
                              unit="mm/day", dates=days, values=vals, spatial=ref.spatial, temporal=TemporalSupport(step="daily", start=start, end=end),
                              data_type="hypothetical_scenario" if syn else "model_estimate", measurement_process="synthetic_demo" if syn else "reanalysis_blend",
                              evidence_id=ev_id, retrieval_mode=ref.retrieval_mode, is_synthetic=syn, caveats=list(ev.caveats))
    return out, ev, []


def climatic_water_balance(rain: Optional[EnvironmentalSeries], et0: Optional[EnvironmentalSeries], start: str, end: str, *, name: str = "Rainfall minus reference ET0",
                           min_coverage: float = DEFAULT_MIN_COVERAGE) -> Feature:
    """P - ET0 over the window (mm). Negative = atmospheric demand exceeded rainfall. Crop-agnostic: no Kc, no soil store."""
    mid = "p_minus_et0"
    params = {"min_coverage": min_coverage}
    sl = [s for s in (rain, et0) if s is not None]
    fid = _fid(mid, [s.series_id for s in sl] or ["<missing>"], start, end, params)
    miss = [n for n, s in (("PRECTOTCORR", rain), ("ET0_FAO56", et0)) if s is None]
    if miss:
        return _insufficient(feature_id=fid, name=name, family="water_balance", unit="mm", start=start, end=end, method_id=mid, params=params, series_list=sl,
                             ins=[missing_variable(m, name) for m in miss])
    a, b = window_array(rain, start, end), window_array(et0, start, end)
    cov, ins = _gate([a, b], min_coverage)
    if ins:
        return _insufficient(feature_id=fid, name=name, family="water_balance", unit="mm", start=start, end=end, method_id=mid, params=params, series_list=sl, ins=[ins], cov=cov)
    ok = np.isfinite(a) & np.isfinite(b)
    p_tot, e_tot = float(a[ok].sum()), float(b[ok].sum())
    base = _base(sl)
    return Feature(feature_id=fid, name=name, family="water_balance", status="computed" if cov.missing_days == 0 else "bounded", value=p_tot - e_tot, unit="mm",
                   window_start=start, window_end=end, method_id=mid, method_params=params, coverage=cov,
                   detail={"rain_mm": round(p_tot, 1), "et0_mm": round(e_tot, 1)},
                   **{**base, "caveats": base["caveats"] + ["Compares rainfall with reference atmospheric demand only; not irrigation requirement (needs Kc, soil, paddy percolation)."]
                      + ([f"{cov.missing_days} missing day(s) excluded from both terms."] if cov.missing_days else [])})


# ------------------------------------------------------------- reliability
def seasonal_reliability(series: Optional[EnvironmentalSeries], *, md_start: str, md_end: str, years: Sequence[int], name: str,
                         min_coverage: float = DEFAULT_MIN_COVERAGE, min_years: int = 10, recommended_years: int = 30,
                         exceedance_probs: Sequence[float] = (0.8, 0.5, 0.2)) -> Feature:
    """Distribution of the window total across years (rainfall reliability for a fixed seasonal window).

    ``md_start``/``md_end`` are 'MM-DD'. Years failing the coverage gate are *excluded and listed*, not imputed.
    Probability-of-exceedance values use the empirical (Weibull-free) linear-interpolation percentile:
    value exceeded with probability p = percentile(100*(1-p)). 80% exceedance ('dependable rain') = 20th percentile.
    Windows that cross New Year (md_end < md_start) end in year+1.
    """
    mid = "seasonal_reliability"
    params = {"md_start": md_start, "md_end": md_end, "min_coverage": min_coverage, "min_years": min_years, "exceedance_probs": list(exceedance_probs)}
    fid = _fid(mid, [series.series_id] if series else ["<missing>"], f"{min(years)}-{md_start}", f"{max(years)}-{md_end}", params)
    w0, w1 = f"{min(years)}-{md_start}", f"{max(years)}-{md_end}"
    if series is None:
        return _insufficient(feature_id=fid, name=name, family="reliability", unit="", start=w0, end=w1, method_id=mid, params=params, series_list=[], ins=[missing_variable("series", name)])
    crosses = md_end < md_start
    per_year, excluded = {}, {}
    for y in years:
        s, e = f"{y}-{md_start}", f"{y + (1 if crosses else 0)}-{md_end}"
        arr = window_array(series, s, e)
        cov = _coverage(arr)
        if cov.fraction >= min_coverage:
            per_year[y] = float(np.nansum(arr))
        else:
            excluded[y] = round(cov.fraction, 3)
    n = len(per_year)
    if n < min_years:
        return _insufficient(feature_id=fid, name=name, family="reliability", unit=series.unit, start=w0, end=w1, method_id=mid, params=params, series_list=[series],
                             ins=[Insufficiency(code=InsufficiencyCode.sample_too_small, message=f"Only {n} usable seasons (< {min_years}); percentiles would be unreliable",
                                                remedy="Request a longer POWER record (1981-present available).")])
    vals = np.array(list(per_year.values()))
    q = {f"p_exceed_{int(p * 100)}": float(np.percentile(vals, 100 * (1 - p))) for p in exceedance_probs}
    base = _base([series])
    cav = list(base["caveats"])
    ins = []
    if n < recommended_years:
        ins.append(Insufficiency(code=InsufficiencyCode.sample_too_small, severity="degrading",
                                 message=f"{n} seasons used; climatological practice prefers >= {recommended_years}. Treat quantiles as indicative."))
    if excluded:
        cav.append(f"Excluded years (coverage below {min_coverage:.0%}): {sorted(excluded)}")
    return Feature(feature_id=fid, name=name, family="reliability", status="computed", value=float(np.median(vals)), unit=series.unit, window_start=w0, window_end=w1,
                   method_id=mid, method_params=params, coverage=None, insufficiency=ins,
                   detail={"n_years": n, "per_year": {str(k): round(v, 1) for k, v in per_year.items()}, "excluded_years": {str(k): v for k, v in excluded.items()},
                           "mean": float(vals.mean()), "std": float(vals.std(ddof=1)) if n > 1 else None, "cv": float(vals.std(ddof=1) / vals.mean()) if vals.mean() else None,
                           "quantiles_by_exceedance": q, "percentile_method": "numpy linear interpolation"},
                   **{**base, "caveats": cav})
