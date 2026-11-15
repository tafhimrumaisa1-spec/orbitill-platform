"""Native grids, footprints and the *no false spatial precision* guard.

POWER (per the official API tutorial, verified in-session): meteorology is
delivered at 0.5 deg (lat) x 0.625 deg (lon), solar at 1 x 1 deg. IMERG Final is
0.1 x 0.1 deg. HLS is 30 m. SMAP enhanced L3 is a 9 km EASE-Grid 2.0 product.

Cell-centre conventions
-----------------------
* MERRA-2 (POWER meteorology): grid *points* at lat = -90 + 0.5*i and
  lon = -180 + 0.625*j; each value represents the surrounding 0.5 x 0.625 box.
* CERES SYN1deg (POWER solar): 1-degree boxes with integer-degree edges.
* IMERG: 0.1-degree boxes with edges at multiples of 0.1.
These conventions are asserted by tests against hand-computed Rajshahi cells.
If a live response ever contradicts them, the live adapter records the mismatch
(``cell_convention_check``) rather than silently trusting this module.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .schemas import Insufficiency, InsufficiencyCode, SpatialSupport

KM_PER_DEG_LAT = 111.32  # mean metres/degree are close enough for footprint *labels*
KM_PER_DEG_LON_EQ = 111.32


@dataclass(frozen=True)
class GridSpec:
    name: str
    dlat: float
    dlon: float
    kind: str  # 'points' (centres on lattice) or 'boxes' (edges on lattice)
    lat0: float = 0.0
    lon0: float = 0.0


MERRA2 = GridSpec("MERRA-2 0.5x0.625", 0.5, 0.625, "points", -90.0, -180.0)
CERES_1DEG = GridSpec("CERES SYN1deg 1x1", 1.0, 1.0, "boxes", -90.0, -180.0)
IMERG_01 = GridSpec("IMERG 0.1x0.1", 0.1, 0.1, "boxes", -90.0, -180.0)


@dataclass(frozen=True)
class Cell:
    grid: str
    center_lat: float
    center_lon: float
    south: float
    north: float
    west: float
    east: float

    @property
    def cell_id(self) -> str:
        return f"{self.grid}|{self.center_lat:.4f},{self.center_lon:.4f}"

    @property
    def bbox_wsen(self) -> tuple[float, float, float, float]:
        return (self.west, self.south, self.east, self.north)

    def footprint_km(self) -> tuple[float, float]:
        ns = (self.north - self.south) * KM_PER_DEG_LAT
        ew = (self.east - self.west) * KM_PER_DEG_LON_EQ * math.cos(math.radians(self.center_lat))
        return round(ns, 1), round(ew, 1)

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east


def _norm_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def cell_for(lat: float, lon: float, spec: GridSpec) -> Cell:
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    lon = _norm_lon(lon)
    if spec.kind == "points":
        i = round((lat - spec.lat0) / spec.dlat)
        j = round((lon - spec.lon0) / spec.dlon)
        clat = spec.lat0 + i * spec.dlat
        clon = spec.lon0 + j * spec.dlon
    else:
        i = math.floor((lat - spec.lat0) / spec.dlat + 1e-12)
        j = math.floor((lon - spec.lon0) / spec.dlon + 1e-12)
        clat = spec.lat0 + (i + 0.5) * spec.dlat
        clon = spec.lon0 + (j + 0.5) * spec.dlon
    clat, clon = round(clat, 6), round(clon, 6)
    return Cell(
        spec.name,
        clat,
        clon,
        max(-90.0, round(clat - spec.dlat / 2, 6)),
        min(90.0, round(clat + spec.dlat / 2, 6)),
        round(clon - spec.dlon / 2, 6),
        round(clon + spec.dlon / 2, 6),
    )


def spatial_support_for(lat: float, lon: float, spec: GridSpec, note: str | None = None) -> SpatialSupport:
    c = cell_for(lat, lon, spec)
    ns, ew = c.footprint_km()
    return SpatialSupport(
        kind="grid_cell",
        requested_lat=lat,
        requested_lon=lon,
        native_resolution_lat_deg=spec.dlat,
        native_resolution_lon_deg=spec.dlon,
        footprint_bbox_wsen=c.bbox_wsen,
        footprint_km_ns=ns,
        footprint_km_ew=ew,
        cell_id=c.cell_id,
        note=note
        or f"Value represents the whole {spec.name} grid cell (~{ns:.0f} x {ew:.0f} km), not the requested point.",
    )


class FalsePrecisionError(ValueError):
    """Raised when something would present data finer than its native resolution."""

    def to_insufficiency(self) -> Insufficiency:
        return Insufficiency(
            code=InsufficiencyCode.resolution_mismatch,
            message=str(self),
            remedy="Report at native resolution, or bring in an independent finer-resolution source.",
        )


def assert_not_finer_than_native(target_dlat: float, target_dlon: float, native_dlat: float, native_dlon: float) -> None:
    """Refuse requests to resample *to* a grid finer than the source supports."""
    if target_dlat < native_dlat - 1e-12 or target_dlon < native_dlon - 1e-12:
        raise FalsePrecisionError(
            f"Requested {target_dlat}x{target_dlon} deg is finer than native "
            f"{native_dlat}x{native_dlon} deg; interpolation would create fake spatial precision."
        )


def aggregate_to_footprint(fine_values: list[float | None], fine_dlat: float, fine_dlon: float, coarse: Cell) -> dict:
    """Area-mean of *finer* cells that fall inside a coarser footprint (legitimate upscaling).

    ``fine_values`` must be the full set of fine cells inside ``coarse`` (row-major);
    if too many are missing the aggregate is withheld (typed), not extrapolated.
    """
    n_expected = round(((coarse.north - coarse.south) / fine_dlat) * ((coarse.east - coarse.west) / fine_dlon))
    valid = [v for v in fine_values if v is not None and not math.isnan(v)]
    frac = len(valid) / n_expected if n_expected else 0.0
    if frac < 0.8:
        return {"value": None, "valid_fraction": frac, "n_expected": n_expected,
                "insufficiency": Insufficiency(code=InsufficiencyCode.insufficient_coverage,
                                               message=f"Only {len(valid)}/{n_expected} fine cells valid inside footprint").model_dump()}
    return {"value": sum(valid) / len(valid), "valid_fraction": frac, "n_expected": n_expected, "insufficiency": None}


def footprint_label(spatial: SpatialSupport) -> str:
    """Human legend text for maps/charts: always state native resolution."""
    if spatial.native_resolution_m:
        return f"native {spatial.native_resolution_m:g} m pixel"
    if spatial.footprint_km_ns and spatial.footprint_km_ew:
        return (f"native {spatial.native_resolution_lat_deg:g}° x {spatial.native_resolution_lon_deg:g}° cell "
                f"(≈{spatial.footprint_km_ns:.0f} x {spatial.footprint_km_ew:.0f} km)")
    return "native resolution unknown"
