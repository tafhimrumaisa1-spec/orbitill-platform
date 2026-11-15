"""HLS (Harmonized Landsat Sentinel-2) NDVI computation with cloud/QA masking.

Scope: pure-array processing for a field of pixels extracted elsewhere (AppEEARS / earthaccess / STAC).
No raster download happens here. HLS v2.0 conventions used (HLS v2.0 user guide; NOT re-verified in this build
because LP DAAC was unreachable - confirm before publishing):
  * surface reflectance stored as int16 with scale factor 0.0001, fill -9999
  * HLSL30 (Landsat 8/9): red=B04, NIR=B05.   HLSS30 (Sentinel-2): red=B04, NIR=B8A (30 m resampled)
  * Fmask bits: 0 cirrus, 1 cloud, 2 adjacent to cloud/shadow, 3 cloud shadow, 4 snow/ice, 5 water, 6-7 aerosol level
NDVI is greenness, not yield, nutrient status, disease or crop identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from ..schemas import Insufficiency, InsufficiencyCode

SCALE = 0.0001
FILL = -9999
BANDS = {"HLSL30": {"red": "B04", "nir": "B05"}, "HLSS30": {"red": "B04", "nir": "B8A"}}
PIXEL_M = 30.0
PIXEL_HA = (PIXEL_M ** 2) / 10_000.0  # 0.09 ha


def decode_fmask(fmask: np.ndarray) -> dict[str, np.ndarray]:
    f = np.asarray(fmask).astype(np.uint16)
    return {"cirrus": (f & 1) > 0, "cloud": (f & 2) > 0, "adjacent": (f & 4) > 0, "shadow": (f & 8) > 0,
            "snow_ice": (f & 16) > 0, "water": (f & 32) > 0, "aerosol_level": (f >> 6) & 3}


def ndvi_from_dn(red_dn, nir_dn, fmask=None, *, mask_water: bool = True, mask_snow: bool = True, max_aerosol_level: int = 2) -> tuple[np.ndarray, dict]:
    """NDVI = (NIR - Red) / (NIR + Red) on scaled reflectance. Masked pixels -> NaN. Returns (ndvi, counts)."""
    red = np.asarray(red_dn, dtype=float)
    nir = np.asarray(nir_dn, dtype=float)
    bad = (red == FILL) | (nir == FILL)
    r, n = red * SCALE, nir * SCALE
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (n - r) / (n + r)
    counts = {"total": int(red.size), "fill": int(bad.sum())}
    mask = bad | ~np.isfinite(ndvi) | (r < 0) | (n < 0)
    if fmask is not None:
        m = decode_fmask(fmask)
        qa = m["cloud"] | m["adjacent"] | m["shadow"] | m["cirrus"] | (m["aerosol_level"] > max_aerosol_level)
        if mask_snow:
            qa |= m["snow_ice"]
        if mask_water:
            qa |= m["water"]
        counts.update(cloud=int(m["cloud"].sum()), shadow=int(m["shadow"].sum()), adjacent=int(m["adjacent"].sum()), water=int(m["water"].sum()))
        mask |= qa
    ndvi = np.where(mask, np.nan, np.clip(ndvi, -1.0, 1.0))
    counts["valid"] = int(np.isfinite(ndvi).sum())
    return ndvi, counts


@dataclass
class FieldNDVI:
    status: str                      # computed | insufficient
    median: Optional[float]
    mean: Optional[float]
    p10: Optional[float]
    p90: Optional[float]
    n_pixels_field: int
    n_valid: int
    valid_fraction: float
    field_area_ha: float
    insufficiency: list[Insufficiency]


def field_ndvi(ndvi: np.ndarray, field_mask: np.ndarray, *, min_pixels: int = 4, min_valid_fraction: float = 0.5) -> FieldNDVI:
    """Zonal NDVI statistics for a field footprint on the 30 m HLS grid.

    Refuses (typed) when the field is smaller than ``min_pixels`` HLS pixels (mixed-pixel dominated; 4 px = 0.36 ha) or when
    too few pixels survive cloud masking. Smallholder plots in Bangladesh are often < 0.4 ha: this gate is expected to
    trigger there and the correct output is 'insufficient resolution', not a number.
    """
    fm = np.asarray(field_mask, dtype=bool)
    n_field = int(fm.sum())
    area = n_field * PIXEL_HA
    ins: list[Insufficiency] = []
    if n_field < min_pixels:
        ins.append(Insufficiency(code=InsufficiencyCode.resolution_mismatch,
                                 message=f"Field covers {n_field} HLS pixels (~{area:.2f} ha); need >= {min_pixels} for a field-level NDVI. 30 m pixels would be mixed with neighbours.",
                                 remedy="Report NDVI as landscape context for the surrounding block, or use finer imagery (e.g. 10 m Sentinel-2 bands directly)."))
        return FieldNDVI("insufficient", None, None, None, None, n_field, 0, 0.0, area, ins)
    vals = ndvi[fm]
    valid = vals[np.isfinite(vals)]
    frac = len(valid) / n_field
    if frac < min_valid_fraction:
        ins.append(Insufficiency(code=InsufficiencyCode.insufficient_coverage,
                                 message=f"Only {len(valid)}/{n_field} field pixels are cloud/QA-clean ({frac:.0%}); need >= {min_valid_fraction:.0%}",
                                 remedy="Use another acquisition date; do not interpolate across clouds."))
        return FieldNDVI("insufficient", None, None, None, None, n_field, len(valid), frac, area, ins)
    return FieldNDVI("computed", float(np.median(valid)), float(valid.mean()), float(np.percentile(valid, 10)), float(np.percentile(valid, 90)),
                     n_field, len(valid), frac, area, [])


def ndvi_time_series(scenes: Sequence[dict], field_mask: np.ndarray, **kw) -> list[dict]:
    """Scenes: dicts with keys date, sensor ('HLSL30'|'HLSS30'), red, nir, fmask. Returns one record per scene incl. rejected ones.

    Rejected scenes are kept (status insufficient) so cloudiness is visible instead of silently thinning the series.
    """
    out = []
    for sc in sorted(scenes, key=lambda s: s["date"]):
        nd, counts = ndvi_from_dn(sc["red"], sc["nir"], sc.get("fmask"))
        st = field_ndvi(nd, field_mask, **kw)
        out.append({"date": sc["date"], "sensor": sc["sensor"], "bands": BANDS[sc["sensor"]], "status": st.status, "median_ndvi": st.median,
                    "valid_fraction": st.valid_fraction, "n_valid": st.n_valid, "counts": counts, "insufficiency": [i.model_dump(mode="json") for i in st.insufficiency]})
    return out
