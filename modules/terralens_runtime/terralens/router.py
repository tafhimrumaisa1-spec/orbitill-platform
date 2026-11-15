"""Region Intelligence Router.

``get_region_profile(lat, lon)`` is the canonical entry point. It resolves the
country and administrative chain, selects a region pack or an explicit
"no pack" exploration state, and returns datasets, readiness gates, limitations
and typed unknowns. It never returns ``validated_with_evidence``.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from . import catalog, data, geometry
from .types import (
    SCHEMA_VERSION,
    AdminUnitRef,
    AnalysisGate,
    Availability,
    CountryRef,
    FarmerModeLink,
    FeatureFlags,
    GridFootprint,
    Insufficiency,
    LocationBlock,
    Readiness,
    RegionBlock,
    RegionProfile,
    Status,
    TypedUnknown,
)

WORLD_BBOX = [-180.0, -85.0, 180.0, 85.0]

BD_ROLES = {1: "division", 2: "district", 3: "upazila_or_thana"}
US_ROLES = {1: "state", 2: "county"}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _admin_ref(feature: dict) -> AdminUnitRef:
    props = feature["properties"]
    if props["countryCode"] == "BD":
        role = BD_ROLES.get(props["level"], "administrative_unit")
    elif props["countryCode"] == "US":
        role = US_ROLES.get(props["level"], "administrative_unit")
        if role == "county" and props["name"] == "Story":
            role = "pilot_county"
    else:
        role = "administrative_unit"
    return AdminUnitRef(
        level=props["level"],
        id=props["id"],
        name=props["name"],
        name_bn=props.get("nameBn"),
        role=role,
        source_id=props["sourceId"],
        license=props["license"],
        centroid=props.get("centroid"),
    )


def _country_ref(feature: dict) -> CountryRef:
    props = feature["properties"]
    return CountryRef(
        id=props["id"],
        code=props.get("countryCode") or props["id"].replace("COUNTRY-", ""),
        name=props["name"],
        name_bn=props.get("nameBn"),
        source_id=props["sourceId"],
        license=props["license"],
        bbox=props["bbox"],
        representative_point=props["centroid"],
    )


def _nominal_square(lat: float, lon: float, side_km: float, grid_name: str, note: str) -> GridFootprint:
    half_lat = side_km / 2.0 / geometry.KM_PER_DEG_LAT
    half_lon = side_km / 2.0 / (geometry.KM_PER_DEG_LON_EQ * max(0.05, math.cos(math.radians(lat))))
    west, east = round(lon - half_lon, 6), round(lon + half_lon, 6)
    south, north = round(lat - half_lat, 6), round(lat + half_lat, 6)
    return GridFootprint(
        grid=grid_name,
        center_lat=round(lat, 6),
        center_lon=round(lon, 6),
        west=west,
        south=south,
        east=east,
        north=north,
        footprint_km_ns=round((north - south) * geometry.KM_PER_DEG_LAT, 1),
        footprint_km_ew=round((east - west) * geometry.KM_PER_DEG_LON_EQ * math.cos(math.radians(lat)), 1),
        cell_id=f"{grid_name}|nominal@{lat:.4f},{lon:.4f}",
        note=note,
    )


def _footprints(lat: float, lon: float) -> dict[str, GridFootprint]:
    def to_grid(payload: dict) -> GridFootprint:
        return GridFootprint(
            grid=payload["grid"],
            center_lat=payload["centerLat"],
            center_lon=payload["centerLon"],
            west=payload["west"],
            south=payload["south"],
            east=payload["east"],
            north=payload["north"],
            footprint_km_ns=payload["footprintKmNs"],
            footprint_km_ew=payload["footprintKmEw"],
            cell_id=payload["cellId"],
            note=payload["note"],
        )

    return {
        "powerMeteorology": to_grid(geometry.cell_for(lat, lon, geometry.MERRA2)),
        "powerSolar": to_grid(geometry.cell_for(lat, lon, geometry.CERES_1DEG)),
        "imerg": to_grid(geometry.cell_for(lat, lon, geometry.IMERG_01)),
        "smapNominal": _nominal_square(
            lat,
            lon,
            9.0,
            "SMAP L4 9 km output grid (nominal)",
            (
                "A nominal 9 km square drawn around the point. It is not the exact EASE-Grid 2.0 "
                "cell index, and the SMAP radiometer footprint is about 36 km. The product is a "
                "model assimilation, not a farm measurement."
            ),
        ),
    }


def _clamp(gate: AnalysisGate, cap: Readiness) -> AnalysisGate:
    from .types import READINESS_ORDER

    if READINESS_ORDER.index(gate.readiness) > READINESS_ORDER.index(cap):
        gate.readiness = cap
    return gate


def _extent(region_id: str, country: dict | None) -> dict:
    store = data.store()
    if region_id in ("BD-RAJ-BARIND", "BD-COASTAL", "US-IA-STORY", "US-IA"):
        extent = store.pack_extent(region_id)
        return {
            "bbox": extent["bbox"],
            "anchor": extent["anchor"],
            "area": extent["approxAreaKm2"],
            "admin2Ids": extent["admin2Ids"] if region_id in ("BD-RAJ-BARIND", "BD-COASTAL", "US-IA-STORY") else [],
        }
    if country:
        props = country["properties"]
        return {
            "bbox": props["bbox"],
            "anchor": props["centroid"],
            "area": props.get("areaKm2"),
            "admin2Ids": [],
        }
    return {"bbox": list(WORLD_BBOX), "anchor": [0.0, 20.0], "area": None, "admin2Ids": []}


def _region_block(region_id: str, country: dict | None) -> RegionBlock:
    pack = catalog.region_pack(region_id)
    extent = _extent(region_id, country)
    return RegionBlock(
        region_id=pack["regionId"],
        label=pack["label"],
        label_bn=pack["labelBn"],
        mode=pack["mode"],
        readiness_cap=pack["readinessCap"],
        pack_status=pack["packStatus"],
        extent_basis=pack["extentBasis"],
        description=pack["description"],
        admin2_ids=extent["admin2Ids"],
        approx_area_km2=extent["area"],
        bbox=extent["bbox"],
        representative_point=extent["anchor"],
        parent_region_id=pack.get("parentRegionId"),
    )


def _unknowns(region_id: str, on_land: bool, has_field: bool) -> list[TypedUnknown]:
    entries = [
        TypedUnknown(
            name="field_soil_measurement",
            state="unknown",
            reason="No soil sample or laboratory result is bundled for this location.",
            source_needed="Dated field soil test (texture, organic matter, pH, salinity where relevant).",
        ),
        TypedUnknown(
            name="verified_local_prices_and_costs",
            state="unknown",
            reason="No dated local market, input or labour cost series is bundled.",
            source_needed="Dated local price and cost basis from a trusted regional source.",
        ),
        TypedUnknown(
            name=("selected_field_geometry" if not has_field else "field_boundary_accuracy"),
            state="unknown",
            reason=(
                "No field polygon has been drawn yet; only a point or administrative location is known."
                if not has_field
                else "A hand-drawn polygon is not a surveyed boundary and has no positional-accuracy statement."
            ),
            source_needed="Surveyed or GNSS field boundary with an accuracy estimate.",
        ),
    ]
    if not on_land:
        entries.insert(
            0,
            TypedUnknown(
                name="administrative_unit",
                state="unknown",
                reason="The coordinate is not inside a bundled country polygon, so no administrative unit is assigned.",
                source_needed="A coordinate on land inside a supported boundary dataset.",
            ),
        )
    if region_id == "BD-COASTAL":
        entries.insert(
            0,
            TypedUnknown(
                name="dated_salinity_measurement",
                state="unknown",
                reason="Coastal soil and water advice is salinity-gated; no dated salinity evidence is bundled.",
                source_needed="Dated soil or irrigation-water electrical conductivity / salinity measurement.",
            ),
        )
    if region_id in ("US-IA-STORY", "US-IA", "US-NATIONAL"):
        entries.insert(
            0,
            TypedUnknown(
                name="integrated_usda_soil_evidence",
                state="unknown",
                reason="USDA soil and crop evidence is an integration requirement and is not present in this module.",
                source_needed="USDA soil survey and crop layer integration via the owning science service.",
            ),
        )
    if region_id in ("GLOBAL", "BD-NATIONAL", "US-NATIONAL"):
        entries.insert(
            1,
            TypedUnknown(
                name="local_crop_calendar",
                state="unknown",
                reason="No local crop calendar is bundled for this region.",
                source_needed="Region-validated crop calendar owned by SoilBrain.",
            ),
        )
    return entries


def _farmer_link(region_id: str, lat: float, lon: float, on_land: bool) -> FarmerModeLink:
    # The integrated release has one runnable downstream decision route: the
    # conditional Barind comparison.  Geography support alone must not imply
    # that a crop model exists for coastal Bangladesh, Iowa, or every national
    # context exposed by this explorer.
    allowed = on_land and region_id == "BD-RAJ-BARIND"
    href = f"/planner.html?region={region_id}&lat={lat:.6f}&lon={lon:.6f}"
    if allowed:
        return FarmerModeLink(allowed=True, href=href)
    reason = (
        "The coordinate is outside bundled land boundaries."
        if not on_land
        else "No runnable decision model is integrated for this region; keep exploring its evidence and limitations."
    )
    return FarmerModeLink(allowed=False, href=href, reason=reason)


def get_region_profile(
    lat: float,
    lon: float,
    *,
    locale: str = "en",
    requested_region: str | None = None,
    has_field: bool = False,
) -> RegionProfile:
    if not -90.0 <= lat <= 90.0:
        raise ValueError(f"latitude out of range: {lat}")
    if not -180.0 <= lon <= 180.0:
        raise ValueError(f"longitude out of range: {lon}")
    lon = round(geometry.normalize_lon(lon), 10)

    store = data.store()
    warnings: list[str] = []

    country = store.country_at(lat, lon)
    country_code = country["properties"].get("countryCode") if country else None

    chain: list[dict] = []
    if country_code == "BD":
        chain = store.bd_chain(lat, lon)
    elif country_code == "US":
        chain = store.us_chain(lat, lon)

    region_id, resolution_reason = store.resolve_region(country_code, chain)

    if requested_region:
        if requested_region not in catalog.REGION_PACKS:
            warnings.append(f"Unknown requested region {requested_region!r}; resolved {region_id} instead.")
        elif requested_region != region_id:
            warnings.append(
                f"Requested region {requested_region} does not cover this coordinate; resolved {region_id}."
            )

    pack = catalog.region_pack(region_id)
    area = _region_block(region_id, country)

    gates: dict[str, AnalysisGate] = {}
    for name, gate in catalog.analysis_gates(region_id, len(chain)).items():
        gates[name] = _clamp(gate, pack["readinessCap"])

    overall = catalog.clamp_readiness(gates, pack["readinessCap"])
    if overall is Readiness.VALIDATED_WITH_EVIDENCE:  # defensive; caps never allow it
        overall = Readiness.RESEARCH_PILOT

    on_land = country is not None
    inside_pilot = region_id in ("BD-RAJ-BARIND", "BD-COASTAL", "US-IA-STORY")
    admin_refs = [_admin_ref(feature) for feature in chain]

    nearest_km = None
    if not on_land:
        nearest_km, nearest_name = store.distance_to_nearest_country_km(lat, lon)
        if nearest_name:
            warnings.append(f"No country polygon contains this point; nearest land is {nearest_name}.")
        else:
            warnings.append("No bundled country polygon contains this point and no nearby land was found.")

    datasets = catalog.datasets_for(country_code)
    dataset_ids = {d.source_id for d in datasets}
    boundary_sources: list[str] = []
    if country_code == "BD":
        boundary_sources = [
            "geoboundaries-BGD-ADM1", "geoboundaries-BGD-ADM2",
            "geoboundaries-BGD-ADM3", "openadmindata-bd-names",
        ]
    elif country_code == "US":
        boundary_sources = ["geoboundaries-USA-ADM1", "geoboundaries-USA-ADM2"]
    else:
        boundary_sources = ["naturalearth-50m-countries"]

    limitations = list(pack["limitations"])
    if not on_land:
        limitations.insert(0, "Exploration only: the coordinate is outside bundled country boundaries, so no administrative or field context is available.")
    if abs(lat) > 60.0:
        limitations.append(
            "Polar latitude (|lat| > 60°): agricultural interpretation is out of scope and several NASA "
            "land products are masked over ice sheets. Treat this as geographic exploration only."
        )
    if region_id == "BD-NATIONAL":
        limitations.append("The national pack carries no pilot claim; readiness is capped at conditional.")

    missing: list[str] = []
    for gate in gates.values():
        for item in gate.missing:
            if item not in missing:
                missing.append(item)

    refusal = None
    if not on_land:
        refusal = Insufficiency(
            code="outside_land_boundaries",
            message=(
                "The coordinate is not inside a bundled country polygon. Global gridded context may "
                "exist, but this router refuses to assign an administrative region or field-level meaning."
            ),
            missing=["administrative_unit", "field_boundary"],
            remedy="Enter a coordinate on land, or search for a district or county by name.",
            severity="blocking",
        )

    profile = RegionProfile(
        schema_version=SCHEMA_VERSION,
        generated_at_utc=utcnow(),
        data_version=store.data_version,
        status=Status.OK,
        query={
            "lat": lat,
            "lon": lon,
            "locale": locale,
            "requestedRegionId": requested_region,
            "resolutionReason": resolution_reason,
        },
        location=LocationBlock(
            lat=round(lat, 6),
            lon=round(lon, 6),
            on_land=on_land,
            country_code=country_code,
            admin_depth=len(chain),
            inside_pilot_extent=inside_pilot,
            nearest_admin_km=nearest_km,
            bbox=area.bbox or list(WORLD_BBOX),
        ),
        country=_country_ref(country) if country else None,
        admin=admin_refs,
        region=area,
        readiness_overall=overall,
        analyses=gates,
        datasets=datasets,
        feature_flags=FeatureFlags(
            field_selection=on_land,
            upazila_browsing=country_code == "BD",
            county_browsing=country_code == "US" and any(
                ref.name == "Iowa" and ref.level == 1 for ref in admin_refs
            ),
            salinity_gate=region_id == "BD-COASTAL",
            global_explorer=True,
            offline_atlas=True,
            online_raster_layers=True,
            crop_rules_in_router=False,
            claims_field_measurements=False,
            validated_region_pack=False,
        ),
        limitations=limitations,
        missing_requirements=missing,
        unknowns=_unknowns(region_id, on_land, has_field),
        sources=catalog.source_list(boundary_sources + sorted(dataset_ids) + [catalog.GIBS]),
        footprints=_footprints(lat, lon),
        farmer_mode=_farmer_link(region_id, lat, lon, on_land),
        refusal=refusal,
        warnings=warnings,
    )
    return profile


def region_packs() -> list[dict]:
    """Pilot/region cards for the UI. Uses the same extents as the router."""
    store = data.store()
    out = []
    for region_id, pack in catalog.REGION_PACKS.items():
        extent = _extent(region_id, None)
        if region_id.startswith("BD"):
            country = store.country_by_code("BD")
        elif region_id.startswith("US"):
            country = store.country_by_code("US")
        else:
            country = None
        if country and region_id in ("BD-NATIONAL", "US-NATIONAL", "GLOBAL"):
            extent = _extent(region_id, country)
        out.append({
            "regionId": region_id,
            "label": pack["label"],
            "labelBn": pack["labelBn"],
            "mode": pack["mode"],
            "readinessCap": pack["readinessCap"].value,
            "packStatus": pack["packStatus"],
            "extentBasis": pack["extentBasis"],
            "description": pack["description"],
            "limitations": pack["limitations"],
            "bbox": extent["bbox"],
            "representativePoint": extent["anchor"],
            "approxAreaKm2": extent["area"],
            "admin2Ids": extent["admin2Ids"],
            "parentRegionId": pack.get("parentRegionId"),
        })
    return out
