"""Farm location and field-polygon selection.

A drawn polygon is treated as a *user-drawn boundary*, never a survey. The
module validates it, computes spherical area/perimeter, attaches the region
profile at its label point, and compares the field with the native footprint of
each dataset so the UI can say "this field is 0.4% of one SMAP grid cell"
instead of pretending a grid value belongs to the field.
"""
from __future__ import annotations

import hashlib
import json
import math

from . import catalog, data, geometry
from .router import get_region_profile
from .types import (
    SELECTION_SCHEMA_VERSION,
    FarmSelection,
    FootprintComparison,
    Insufficiency,
    Precision,
    Status,
)

MIN_FIELD_HA = 0.005      # 50 m2: below this a polygon is almost certainly a mis-click
WARN_FIELD_HA = 500.0     # 5 km2: legal as a large holding, but call it out
MAX_FIELD_HA = 5000.0     # 50 km2: above this it is not a "field" for this product
MAX_VERTICES = 2000       # per ring, keeps validation bounded


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _clean_position(position, errors: list[Insufficiency]) -> list[float] | None:
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        return None
    try:
        lon = float(position[0])
        lat = float(position[1])
    except (TypeError, ValueError):
        return None
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        return None
    return [round(lon, 7), round(lat, 7)]


def validate_geometry(raw) -> tuple[dict | None, list[Insufficiency]]:
    """Return a cleaned WGS84 geometry or None plus typed insufficiencies."""
    errors: list[Insufficiency] = []
    if not isinstance(raw, dict):
        return None, [Insufficiency(
            code="geometry_missing",
            message="No GeoJSON geometry was supplied.",
            remedy="Send a GeoJSON Polygon or MultiPolygon in the request body.",
        )]

    gtype = raw.get("type")
    if gtype not in ("Polygon", "MultiPolygon"):
        return None, [Insufficiency(
            code="geometry_type_unsupported",
            message=f"Geometry type {gtype!r} is not accepted; only Polygon and MultiPolygon are.",
            remedy="Convert the boundary to a GeoJSON Polygon or MultiPolygon (WGS84).",
        )]

    coordinates = raw.get("coordinates")
    polygons = [coordinates] if gtype == "Polygon" else coordinates
    if not isinstance(polygons, list) or not polygons:
        return None, [Insufficiency(
            code="geometry_empty",
            message="The geometry contains no polygons.",
            remedy="Draw at least one closed ring.",
        )]

    cleaned_polygons = []
    total_vertices = 0
    for poly_index, polygon in enumerate(polygons):
        if not isinstance(polygon, list) or not polygon:
            errors.append(Insufficiency(
                code="geometry_ring_empty",
                message=f"Polygon {poly_index} has no rings.",
                severity="blocking",
            ))
            continue
        cleaned_rings = []
        for ring_index, ring in enumerate(polygon):
            if not isinstance(ring, list) or len(ring) < 4:
                errors.append(Insufficiency(
                    code="ring_too_short",
                    message=f"Ring {ring_index} of polygon {poly_index} has fewer than 4 positions.",
                    remedy="A closed ring needs at least 3 distinct positions plus the repeated first position.",
                ))
                continue
            total_vertices += len(ring)
            if total_vertices > MAX_VERTICES:
                return None, [Insufficiency(
                    code="geometry_too_complex",
                    message=f"The field boundary exceeds {MAX_VERTICES} vertices per polygon.",
                    remedy="Simplify the boundary; field mode is for fields, not administrative polygons.",
                )]
            positions = []
            bad = 0
            for position in ring:
                cleaned = _clean_position(position, errors)
                if cleaned is None:
                    bad += 1
                    continue
                positions.append(cleaned)
            if bad:
                errors.append(Insufficiency(
                    code="position_invalid",
                    message=f"{bad} position(s) in ring {ring_index} are outside WGS84 range or not numeric.",
                    remedy="Use decimal degrees: longitude -180..180, latitude -90..90.",
                ))
                continue
            if positions[0] != positions[-1]:
                errors.append(Insufficiency(
                    code="ring_not_closed",
                    message=f"Ring {ring_index} of polygon {poly_index} is not closed.",
                    remedy="Repeat the first position as the last position of each ring.",
                ))
                continue
            if geometry.ring_self_intersects(positions):
                errors.append(Insufficiency(
                    code="ring_self_intersecting",
                    message=f"Ring {ring_index} of polygon {poly_index} crosses itself.",
                    remedy="Redraw the boundary; self-intersection makes area and containment ambiguous.",
                ))
                continue
            if geometry.ring_area_km2(positions) <= 0:
                errors.append(Insufficiency(
                    code="ring_zero_area",
                    message=f"Ring {ring_index} of polygon {poly_index} encloses no area.",
                    remedy="Check that the ring is not a single repeated point or a straight line.",
                ))
                continue
            cleaned_rings.append(positions)
        if cleaned_rings:
            cleaned_polygons.append(cleaned_rings)

    if errors:
        return None, errors

    cleaned_geom = {"type": gtype, "coordinates": cleaned_polygons if gtype == "MultiPolygon" else cleaned_polygons[0]}
    box = geometry.bbox_of_geom(cleaned_geom)
    if box[2] - box[0] > 180.0:
        return None, [Insufficiency(
            code="antimeridian_unsupported",
            message="The boundary spans more than 180° of longitude and crosses the antimeridian.",
            remedy="Split the field at the antimeridian; TerraLens does not unwrap it.",
        )]
    return cleaned_geom, []


def _largest_polygon_label(geom: dict) -> list[float]:
    polygons = list(geometry.iter_polygons(geom))
    largest = max(
        polygons,
        key=lambda poly: geometry.ring_area_km2(poly[0]) if poly else 0.0,
    )
    return geometry.representative_point({"type": "Polygon", "coordinates": largest})


def _point_geometry(lon: float, lat: float) -> dict:
    return {"type": "Point", "coordinates": [round(lon, 7), round(lat, 7)]}


def _selection_id(payload) -> str:
    return "sel_" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()[:16]


def _share(field_ha: float, cell_km2: float) -> float:
    return round((field_ha / 100.0) / cell_km2, 6)


def _compare_footprints(field_ha: float | None, centroid: tuple[float, float]) -> list[FootprintComparison]:
    lat, lon = centroid
    out: list[FootprintComparison] = []
    if field_ha is None:
        return out

    area_m2 = field_ha * 10_000.0

    power = geometry.cell_for(lat, lon, geometry.MERRA2)
    out.append(FootprintComparison(
        dataset_id="power-climate",
        label="NASA POWER meteorology cell",
        native_resolution="0.5° × 0.625°",
        field_share_of_cell=_share(field_ha, power["footprintKm2"]),
        field_spans=f"{_share(field_ha, power['footprintKm2']) * 100:.3f}% of one cell",
        note=(
            f"One cell is about {power['footprintKmNs']:.0f} × {power['footprintKmEw']:.0f} km here. "
            "POWER values describe the whole cell."
        ),
    ))

    imerg = geometry.cell_for(lat, lon, geometry.IMERG_01)
    out.append(FootprintComparison(
        dataset_id="gpm-imerg",
        label="GPM IMERG precipitation cell",
        native_resolution="0.1° × 0.1°",
        field_share_of_cell=_share(field_ha, imerg["footprintKm2"]),
        field_spans=f"{_share(field_ha, imerg['footprintKm2']) * 100:.3f}% of one cell",
        note=f"One cell is about {imerg['footprintKmNs']:.0f} × {imerg['footprintKmEw']:.0f} km. It is not field rainfall.",
    ))

    smap_cell_km2 = 81.0
    out.append(FootprintComparison(
        dataset_id="smap-l4-rootzone",
        label="SMAP L4 root-zone cell (nominal)",
        native_resolution="9 km output grid; ~36 km source footprint",
        field_share_of_cell=_share(field_ha, smap_cell_km2),
        field_spans=f"{_share(field_ha, smap_cell_km2) * 100:.3f}% of one 9 km cell",
        note=(
            "A nominal 9 km cell is ~81 km²; the SMAP radiometer footprint is ~36 km (~1,018 km²). "
            "The L4 value is a landscape-model estimate, never this field's moisture."
        ),
    ))

    out.append(FootprintComparison(
        dataset_id="hls-30m",
        label="HLS 30 m pixels",
        native_resolution="30 m",
        field_share_of_cell=None,
        field_spans=f"≈{max(1, round(area_m2 / 900)):,} pixels",
        note="30 m is the finest bundled evidence, but a 30 m pixel still mixes soil, crop and shadow.",
    ))

    out.append(FootprintComparison(
        dataset_id="modis-ndvi-8day",
        label="MODIS NDVI 250 m pixels",
        native_resolution="250 m",
        field_share_of_cell=None,
        field_spans=f"≈{max(1, round(area_m2 / 62_500)):,} pixels",
        note="An 8-day composite mixes within-pixel conditions and clouds.",
    ))

    return out


def _refused(
    *,
    precision: Precision,
    geometry_payload: dict | None,
    insufficiencies: list[Insufficiency],
    lat: float | None,
    lon: float | None,
    requested_region: str | None,
    warnings: list[str],
) -> FarmSelection:
    selection_id = _selection_id({
        "geometry": geometry_payload,
        "lat": lat,
        "lon": lon,
        "region": requested_region,
    })
    return FarmSelection(
        schema_version=SELECTION_SCHEMA_VERSION,
        selection_id=selection_id,
        precision=precision,
        geometry=geometry_payload,
        centroid=[round(lon, 7), round(lat, 7)] if lon is not None and lat is not None else [0.0, 0.0],
        bbox=[round(lon, 7), round(lat, 7), round(lon, 7), round(lat, 7)] if lon is not None and lat is not None else [0.0, 0.0, 0.0, 0.0],
        area_hectares=None,
        area_acres=None,
        perimeter_km=None,
        region_id="GLOBAL",
        region_label=catalog.REGION_PACKS["GLOBAL"]["label"],
        admin=[],
        country_code=None,
        footprints=[],
        warnings=warnings,
        insufficiencies=insufficiencies,
        status=Status.REFUSED,
    )


def select_field(
    *,
    geometry_payload: dict | None = None,
    lat: float | None = None,
    lon: float | None = None,
    requested_region: str | None = None,
    locale: str = "en",
) -> FarmSelection:
    """Select a field polygon or an approximate point.

    Exactly one of ``geometry_payload`` or ``lat``/``lon`` must be supplied.
    Invalid input returns a refused selection with typed insufficiencies rather
    than raising, so the API can return a stable 200 envelope.
    """
    warnings: list[str] = []

    if geometry_payload is None and (lat is None or lon is None):
        return _refused(
            precision=Precision.POINT_APPROXIMATE,
            geometry_payload=None,
            insufficiencies=[Insufficiency(
                code="selection_missing",
                message="Supply either a GeoJSON polygon or a latitude/longitude point.",
                remedy="POST {\"geometry\":{...}} or {\"lat\":..,\"lon\":..}.",
            )],
            lat=lat,
            lon=lon,
            requested_region=requested_region,
            warnings=warnings,
        )

    if geometry_payload is not None and (lat is not None or lon is not None):
        return _refused(
            precision=Precision.FIELD_POLYGON,
            geometry_payload=geometry_payload,
            insufficiencies=[Insufficiency(
                code="selection_ambiguous",
                message="Supply a polygon or a point, not both.",
                remedy="Remove either the geometry or the lat/lon fields.",
            )],
            lat=lat,
            lon=lon,
            requested_region=requested_region,
            warnings=warnings,
        )

    if geometry_payload is None:
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):  # type: ignore[operator]
            return _refused(
                precision=Precision.POINT_APPROXIMATE,
                geometry_payload=None,
                insufficiencies=[Insufficiency(
                    code="coordinate_out_of_range",
                    message="Latitude must be -90..90 and longitude -180..180.",
                )],
                lat=lat,
                lon=lon,
                requested_region=requested_region,
                warnings=warnings,
            )
        lon = geometry.normalize_lon(lon)  # type: ignore[arg-type]
        profile = get_region_profile(lat, lon, locale=locale, requested_region=requested_region)  # type: ignore[arg-type]
        warnings.append("Point selection is approximate: a coordinate is not a field boundary and has no area.")
        warnings.extend(profile.warnings)
        insufficiencies = [Insufficiency(
            code="point_not_a_field",
            message="The selection is a point, so no field area is computed.",
            missing=["selected_field_geometry"],
            remedy="Draw the field polygon in the map to obtain area and footprint comparisons.",
            severity="warning",
        )]
        if profile.refusal:
            insufficiencies.append(profile.refusal)
        return FarmSelection(
            schema_version=SELECTION_SCHEMA_VERSION,
            selection_id=_selection_id({"point": [round(lon, 7), round(lat, 7)], "region": requested_region}),
            precision=Precision.POINT_APPROXIMATE,
            geometry=_point_geometry(lon, lat),  # type: ignore[arg-type]
            centroid=[round(lon, 7), round(lat, 7)],  # type: ignore[arg-type]
            bbox=[round(lon, 7), round(lat, 7), round(lon, 7), round(lat, 7)],  # type: ignore[arg-type]
            area_hectares=None,
            area_acres=None,
            perimeter_km=None,
            region_id=profile.region.region_id,
            region_label=profile.region.label,
            admin=profile.admin,
            country_code=profile.location.country_code,
            footprints=[],
            warnings=warnings,
            insufficiencies=insufficiencies,
            status=Status.OK if profile.location.on_land else Status.REFUSED,
        )

    geom, errors = validate_geometry(geometry_payload)
    if geom is None:
        return _refused(
            precision=Precision.FIELD_POLYGON,
            geometry_payload=geometry_payload,
            insufficiencies=errors,
            lat=lat,
            lon=lon,
            requested_region=requested_region,
            warnings=warnings,
        )

    area_km2 = geometry.geom_area_km2(geom)
    area_ha = round(area_km2 * 100.0, 4)
    area_acres = round(area_ha * 2.4710538, 3)
    perimeter = round(sum(
        geometry.ring_perimeter_km(ring) for ring in geometry.iter_rings(geom)
    ), 4)
    centroid = _largest_polygon_label(geom)
    bbox = geometry.bbox_of_geom(geom)

    insufficiencies: list[Insufficiency] = []
    if area_ha < MIN_FIELD_HA:
        insufficiencies.append(Insufficiency(
            code="field_too_small",
            message=f"The polygon is {area_ha:.4f} ha, below the {MIN_FIELD_HA} ha minimum.",
            remedy="Redraw a larger field; this is smaller than a plausible management unit.",
        ))
    if area_ha > MAX_FIELD_HA:
        insufficiencies.append(Insufficiency(
            code="field_too_large",
            message=f"The polygon is {area_ha:,.1f} ha, above the {MAX_FIELD_HA:,.0f} ha field-mode limit.",
            remedy="Select a single field or a sub-area; regional extents belong in the region selector.",
        ))
    elif area_ha > WARN_FIELD_HA:
        warnings.append(
            f"The polygon is {area_ha:,.1f} ha. Large holdings are allowed, but footprint comparisons "
            "assume one contiguous management unit."
        )

    profile = get_region_profile(centroid[1], centroid[0], locale=locale, requested_region=requested_region, has_field=True)
    warnings.extend(profile.warnings)
    if profile.refusal and profile.refusal not in insufficiencies:
        insufficiencies.append(profile.refusal)

    warnings.extend([
        "Area is computed on a sphere from the drawn ring; it is not a surveyed area.",
        "The polygon is user-drawn and carries no positional-accuracy statement.",
    ])

    hard_failure = any(i.severity == "blocking" for i in insufficiencies)
    return FarmSelection(
        schema_version=SELECTION_SCHEMA_VERSION,
        selection_id=_selection_id({
            "geometry": geom,
            "region": profile.region.region_id,
            "dataVersion": profile.data_version,
        }),
        precision=Precision.FIELD_POLYGON,
        geometry=geom,
        centroid=[round(centroid[0], 7), round(centroid[1], 7)],
        bbox=[round(v, 7) for v in bbox],
        area_hectares=area_ha,
        area_acres=area_acres,
        perimeter_km=perimeter,
        region_id=profile.region.region_id,
        region_label=profile.region.label,
        admin=profile.admin,
        country_code=profile.location.country_code,
        footprints=_compare_footprints(area_ha, (centroid[1], centroid[0])),
        warnings=warnings,
        insufficiencies=insufficiencies,
        status=Status.REFUSED if hard_failure else Status.OK,
    )
