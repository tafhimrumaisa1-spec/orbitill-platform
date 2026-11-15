"""Geometry helpers (pure stdlib) shared by routing, field checks and the CLI.

All coordinates are WGS84 longitude/latitude in decimal degrees. Area uses the
spherical trapezoid formula on the IUGG mean Earth radius; at farm scale the
error versus an ellipsoidal geodesic is far below the display precision used
here, and the source of every displayed area is stated in the payload.
"""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088
KM_PER_DEG_LAT = 111.32
KM_PER_DEG_LON_EQ = 111.32


def iter_polygons(geometry: dict):
    gtype = geometry.get("type")
    if gtype == "Polygon":
        yield geometry["coordinates"]
    elif gtype == "MultiPolygon":
        for polygon in geometry["coordinates"]:
            yield polygon


def iter_rings(geometry: dict):
    for polygon in iter_polygons(geometry):
        for ring in polygon:
            yield ring


def normalize_lon(lon: float) -> float:
    return ((lon + 180.0) % 360.0) - 180.0


def bbox_of_geom(geometry: dict) -> list[float]:
    xs: list[float] = []
    ys: list[float] = []
    for ring in iter_rings(geometry):
        for point in ring:
            xs.append(point[0])
            ys.append(point[1])
    if not xs:
        raise ValueError("geometry has no coordinates")
    return [min(xs), min(ys), max(xs), max(ys)]


def ring_area_km2(ring) -> float:
    """Signed spherical ring area, returned unsigned."""
    if len(ring) < 4:
        return 0.0
    total = 0.0
    for i in range(len(ring) - 1):
        lon1, lat1 = map(math.radians, ring[i][:2])
        lon2, lat2 = map(math.radians, ring[i + 1][:2])
        total += (lon2 - lon1) * (2 + math.sin(lat1) + math.sin(lat2))
    return abs(total * EARTH_RADIUS_KM * EARTH_RADIUS_KM / 2.0)


def geom_area_km2(geometry: dict) -> float:
    total = 0.0
    for polygon in iter_polygons(geometry):
        if not polygon:
            continue
        total += ring_area_km2(polygon[0])
        for hole in polygon[1:]:
            total -= ring_area_km2(hole)
    return round(max(total, 0.0), 6)


def haversine_km(a, b) -> float:
    lon1, lat1 = map(math.radians, a[:2])
    lon2, lat2 = map(math.radians, b[:2])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def ring_perimeter_km(ring) -> float:
    return sum(haversine_km(ring[i], ring[i + 1]) for i in range(len(ring) - 1))


def point_in_ring(lon: float, lat: float, ring) -> bool:
    """Even-odd ray cast. Boundary points are not guaranteed either way."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def point_in_geom(lon: float, lat: float, geometry: dict) -> bool:
    for polygon in iter_polygons(geometry):
        if not polygon or not point_in_ring(lon, lat, polygon[0]):
            continue
        if any(point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            continue
        return True
    return False


def point_in_bbox(lon: float, lat: float, box) -> bool:
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


def bbox_intersects(a, b) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def representative_point(geometry: dict) -> list[float]:
    """A deterministic point guaranteed inside a polygon when one exists.

    Tries the bbox centre, then a horizontal scanline through nine candidate
    latitudes, keeping the midpoint of the widest interior interval. This is a
    label/seed point, not a population or area centroid; the payload says so.
    """
    box = bbox_of_geom(geometry)
    cx = (box[0] + box[2]) / 2
    cy = (box[1] + box[3]) / 2
    if point_in_geom(cx, cy, geometry):
        return [round(cx, 6), round(cy, 6)]
    best = None
    for fraction in (0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65, 0.3, 0.7):
        y = box[1] + (box[3] - box[1]) * fraction
        crossings: list[float] = []
        for ring in iter_rings(geometry):
            for i in range(len(ring) - 1):
                x1, y1 = ring[i][0], ring[i][1]
                x2, y2 = ring[i + 1][0], ring[i + 1][1]
                if (y1 > y) != (y2 > y):
                    crossings.append(x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-15))
        crossings.sort()
        for i in range(0, len(crossings) - 1, 2):
            mid = (crossings[i] + crossings[i + 1]) / 2
            if point_in_geom(mid, y, geometry):
                width = crossings[i + 1] - crossings[i]
                if best is None or width > best[0]:
                    best = (width, mid, y)
    if best:
        return [round(best[1], 6), round(best[2], 6)]
    return [round(cx, 6), round(cy, 6)]


# --------------------------------------------------------------------------- #
# grid footprints
# --------------------------------------------------------------------------- #
class GridSpec:
    __slots__ = ("name", "dlat", "dlon", "kind", "lat0", "lon0")

    def __init__(self, name, dlat, dlon, kind="boxes", lat0=-90.0, lon0=-180.0):
        self.name = name
        self.dlat = dlat
        self.dlon = dlon
        self.kind = kind
        self.lat0 = lat0
        self.lon0 = lon0


# Conventions copied from EarthSync's gridinfo.py so the two modules agree:
# POWER meteorology values sit at lat = -90 + 0.5*i, lon = -180 + 0.625*j and
# represent a surrounding 0.5 x 0.625 degree cell; POWER solar is 1 x 1 degree;
# IMERG is a 0.1 degree box grid.
MERRA2 = GridSpec("NASA POWER meteorology (MERRA-2)", 0.5, 0.625, "points")
CERES_1DEG = GridSpec("NASA POWER solar (CERES SYN1deg)", 1.0, 1.0, "boxes")
IMERG_01 = GridSpec("GPM IMERG", 0.1, 0.1, "boxes")


def cell_for(lat: float, lon: float, spec: GridSpec) -> dict:
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    lon = normalize_lon(lon)
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
    south = max(-90.0, round(clat - spec.dlat / 2, 6))
    north = min(90.0, round(clat + spec.dlat / 2, 6))
    west = round(clon - spec.dlon / 2, 6)
    east = round(clon + spec.dlon / 2, 6)
    ns = round((north - south) * KM_PER_DEG_LAT, 1)
    ew = round((east - west) * KM_PER_DEG_LON_EQ * math.cos(math.radians(clat)), 1)
    return {
        "grid": spec.name,
        "cellId": f"{spec.name}|{clat:.4f},{clon:.4f}",
        "centerLat": clat,
        "centerLon": clon,
        "west": west,
        "south": south,
        "east": east,
        "north": north,
        "footprintKmNs": ns,
        "footprintKmEw": ew,
        "footprintKm2": round(
            (north - south) * KM_PER_DEG_LAT * (east - west) * KM_PER_DEG_LON_EQ * math.cos(math.radians(clat)),
            1,
        ),
        "note": (
            f"One {spec.name} cell covers about {ns:g} x {ew:g} km here. "
            "The value belongs to the whole cell, not to any point inside it."
        ),
    }


def segments_intersect(p1, p2, p3, p4) -> bool:
    """Proper-or-touching segment intersection, robust enough for field QA."""

    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    def on_segment(a, b, c):
        return (
            min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12
            and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12
        )

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)
    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0):
        return True
    if abs(o1) < 1e-12 and on_segment(p1, p2, p3):
        return True
    if abs(o2) < 1e-12 and on_segment(p1, p2, p4):
        return True
    if abs(o3) < 1e-12 and on_segment(p3, p4, p1):
        return True
    if abs(o4) < 1e-12 and on_segment(p3, p4, p2):
        return True
    return False


def ring_self_intersects(ring) -> bool:
    """Check non-adjacent edge crossings of a closed ring."""
    n = len(ring) - 1
    if n < 4:
        return False
    for i in range(n):
        a1, a2 = ring[i], ring[i + 1]
        for j in range(i + 1, n):
            if j == i or j == (i + 1) % n or (j + 1) % n == i:
                continue
            b1, b2 = ring[j], ring[j + 1]
            if segments_intersect(a1[:2], a2[:2], b1[:2], b2[:2]):
                return True
    return False
