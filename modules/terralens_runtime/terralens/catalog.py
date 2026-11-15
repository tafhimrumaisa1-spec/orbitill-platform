"""Versioned source register, layer catalogue and region packs.

Everything the map can draw is declared here, once, with its native resolution,
units, licence and honest caveat. The web client reads the same catalogue from
``GET /api/layers`` so the legend can never drift from the server contract.
"""
from __future__ import annotations

from .types import (
    AnalysisGate,
    Availability,
    DatasetAvailability,
    Layer,
    Legend,
    LegendStop,
    Readiness,
    SourceRef,
)

SCHEMA_VERSION = "1.0.0"

GIBS = "nasa-gibs-wmts"
GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
GIBS_DOCS = "https://nasa-gibs.github.io/gibs-api-docs/"

# --------------------------------------------------------------------------- #
# source register
# --------------------------------------------------------------------------- #
SOURCES: dict[str, SourceRef] = {
    "geoboundaries-BGD-ADM0": SourceRef(
        id="geoboundaries-BGD-ADM0",
        title="Bangladesh national boundary (geoBoundaries gbOpen ADM0)",
        provider="geoBoundaries / Wikimedia Commons",
        license="CC0 1.0 Universal",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/BGD",
        version="BGD-ADM0-71232402 (2015 release)",
        used_for="Country outline for display and point-in-country checks; 1:1m scale.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="4cfafa6d5250a0aadeefb8737f11604ad1b9b9904585461fee2a5ece4a61a219",
        attribution="geoBoundaries (CC0)",
    ),
    "geoboundaries-BGD-ADM1": SourceRef(
        id="geoboundaries-BGD-ADM1",
        title="Bangladesh divisions (geoBoundaries gbOpen ADM1)",
        provider="geoBoundaries / Wikimedia Commons",
        license="CC0 1.0 Universal",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/BGD",
        version="BGD-ADM1-32408957 (2015 release)",
        used_for="Division boundaries and division-level routing.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="bb91b74c7a7d8a690122b916f5e2f99606d2ce2f18ff938f49d80f15b4ba6aea",
        attribution="geoBoundaries (CC0)",
    ),
    "geoboundaries-BGD-ADM2": SourceRef(
        id="geoboundaries-BGD-ADM2",
        title="Bangladesh districts (geoBoundaries gbOpen ADM2)",
        provider="Bangladesh Bureau of Statistics (BBS) and OCHA ROAP, via geoBoundaries",
        license="CC BY 3.0 IGO",
        license_url="https://creativecommons.org/licenses/by/3.0/igo/",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/BGD",
        version="BGD-ADM2-16705992 (2020 release)",
        used_for="District boundaries, pilot extents and district-level routing.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="7dbdb186f3b8af10417147a99859196fcd89c619fb5c6ac3804251fb6b449b6a",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
    ),
    "geoboundaries-BGD-ADM3": SourceRef(
        id="geoboundaries-BGD-ADM3",
        title="Bangladesh upazila/thana polygons (geoBoundaries gbOpen ADM3)",
        provider="Bangladesh Bureau of Statistics (BBS) and OCHA ROAP, via geoBoundaries",
        license="CC BY 3.0 IGO",
        license_url="https://creativecommons.org/licenses/by/3.0/igo/",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/BGD",
        version="BGD-ADM3-5055444 (2020; 544 polygons incl. metropolitan thanas)",
        used_for="Sub-district browsing and nearest-admin context. Display geometry simplified (see caveat).",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="141dfd271206602793dd0b0af26d4db918be19cff56c1fac46b17dfeb0cbe006",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
    ),
    "geoboundaries-USA-ADM1": SourceRef(
        id="geoboundaries-USA-ADM1",
        title="US states (geoBoundaries gbOpen USA ADM1)",
        provider="US Census Bureau MAF/TIGER, via geoBoundaries",
        license="Public Domain",
        license_url="https://www.census.gov/programs-surveys/geography/technical-documentation/naming-convention/cartographic-boundary-file.html",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/USA",
        version="USA-ADM1-66186276 (2018 release)",
        used_for="US state outlines and the Iowa pilot frame.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="9d7a32244a5c3c2868d039355db2fdd9eb903ef255cfda128decd20bedc0dfbe",
        attribution="US Census Bureau (public domain) via geoBoundaries",
    ),
    "geoboundaries-USA-ADM2": SourceRef(
        id="geoboundaries-USA-ADM2",
        title="Iowa counties (geoBoundaries gbOpen USA ADM2, filtered)",
        provider="US Census Bureau MAF/TIGER, via geoBoundaries",
        license="Public Domain",
        license_url="https://www.census.gov/programs-surveys/geography/technical-documentation/naming-convention/cartographic-boundary-file.html",
        url="https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/USA",
        version="USA-ADM2-52423323 (2018 release)",
        used_for="Story County pilot and Iowa county browsing.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="16249e8d795aaded6a72910a8c72115a073814b25ee902d61ccc9a9490c6641a",
        attribution="US Census Bureau (public domain) via geoBoundaries",
    ),
    "naturalearth-50m-countries": SourceRef(
        id="naturalearth-50m-countries",
        title="Natural Earth 1:50m admin-0 countries",
        provider="Natural Earth",
        license="Public Domain",
        license_url="https://www.naturalearthdata.com/about/terms-of-use/",
        url="https://www.naturalearthdata.com/downloads/50m-cultural-vectors/",
        version="5.1.2",
        used_for="Global country outlines and point-in-country routing.",
        retrieved_at_utc="2026-11-15T13:24:33Z",
        sha256="3e458fc036ad0a66411f2c1e6cac49c5d7bfb81cb1123bc513b22511a2b7fdeb",
        attribution="Natural Earth (public domain)",
    ),
    "openadmindata-bd-names": SourceRef(
        id="openadmindata-bd-names",
        title="Bangla/English names for districts and upazilas",
        provider="Open Admin Data",
        license="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        url="https://openadmindata.org/bd/districts/ ; https://openadmindata.org/bd/upazilas/",
        version="Retrieved 2026-11-15 (64 districts, 495 upazilas)",
        used_for="Bangla display names, attached only after spatial and name agreement.",
        retrieved_at_utc="2026-11-15T13:26:00Z",
        attribution="Open Admin Data (CC BY 4.0)",
    ),
    GIBS: SourceRef(
        id=GIBS,
        title="NASA Global Imagery Browse Services (GIBS) WMTS",
        provider="NASA EOSDIS",
        license="NASA Earth observation data: free and open, attribution requested",
        license_url="https://www.earthdata.nasa.gov/about/esdis/eosdis/gibs",
        url=GIBS_DOCS,
        version="WMTS 1.0.0, EPSG:3857 best-available",
        used_for="Optional online raster tiles. No API key. Not a measurement of any farm.",
        retrieved_at_utc="2026-11-15T13:40:00Z",
        attribution="NASA GIBS / NASA EOSDIS",
    ),
    "nasa-power": SourceRef(
        id="nasa-power",
        title="NASA POWER (MERRA-2 meteorology, CERES SYN1deg solar)",
        provider="NASA Langley Research Center",
        license="NASA open data",
        license_url="https://power.larc.nasa.gov/docs/license/",
        url="https://power.larc.nasa.gov/",
        version="API v2 (advertised only; retrieval owned by EarthSync)",
        used_for="0.5°x0.625° meteorology and 1°x1° solar grid context. No values are served by this module.",
        attribution="NASA POWER",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-gpm-imerg": SourceRef(
        id="nasa-gpm-imerg",
        title="GPM IMERG precipitation rate",
        provider="NASA GPM / JAXA",
        license="NASA open data",
        license_url="https://gpm.nasa.gov/data/license",
        url="https://gpm.nasa.gov/data/imerg",
        version="IMERG (GIBS daily composite)",
        used_for="Regional precipitation context at 0.1° native resolution.",
        attribution="NASA GPM IMERG",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-smap-l4": SourceRef(
        id="nasa-smap-l4",
        title="SMAP L4 root-zone soil moisture (SPL4SMGP)",
        provider="NASA SMAP / NSIDC",
        license="NASA open data",
        license_url="https://nsidc.org/data/user-resources/data-policies",
        url="https://nsidc.org/data/spl4smgp",
        version="L4 12z instantaneous, model value-added",
        used_for="Modeled root-zone context on a 9 km grid; not a farm measurement.",
        attribution="NASA SMAP L4 (SPL4SMGP)",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-modis-ndvi": SourceRef(
        id="nasa-modis-ndvi",
        title="MODIS Terra NDVI (rolling 8-day)",
        provider="NASA MODIS",
        license="NASA open data",
        license_url="https://modis.gsfc.nasa.gov/data/dataprod/",
        url="https://modis.gsfc.nasa.gov/data/dataprod/mod13.php",
        version="MOD13 8-day rolling composite (GIBS)",
        used_for="Vegetation greenness context at 250 m; not a yield estimate.",
        attribution="NASA MODIS",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-hls": SourceRef(
        id="nasa-hls",
        title="Harmonized Landsat Sentinel-2 (HLS) nadir BRDF-adjusted reflectance",
        provider="NASA HLS",
        license="NASA open data",
        license_url="https://hls.gsfc.nasa.gov/",
        url="https://hls.gsfc.nasa.gov/",
        version="HLS L30 (Landsat 8/9) and S30 (Sentinel-2)",
        used_for="30 m surface reflectance context, subject to cloud and compositing.",
        attribution="NASA HLS",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-srtm": SourceRef(
        id="nasa-srtm",
        title="Shuttle Radar Topography Mission elevation",
        provider="NASA / NGA",
        license="NASA open data",
        license_url="https://www2.jpl.nasa.gov/srtm/",
        url="https://www2.jpl.nasa.gov/srtm/",
        version="SRTM 1 arc-second (GIBS colour index)",
        used_for="Terrain context; static 2000 elevation.",
        attribution="NASA SRTM",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "nasa-modis-truecolor": SourceRef(
        id="nasa-modis-truecolor",
        title="MODIS Terra corrected reflectance (true colour)",
        provider="NASA MODIS",
        license="NASA open data",
        license_url="https://modis.gsfc.nasa.gov/",
        url="https://modis.gsfc.nasa.gov/",
        version="Daily global true colour (GIBS)",
        used_for="Visual context only; not an analysis layer.",
        attribution="NASA MODIS",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "maplibre-gl-js": SourceRef(
        id="maplibre-gl-js",
        title="MapLibre GL JS",
        provider="MapLibre",
        license="BSD-3-Clause",
        license_url="https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt",
        url="https://maplibre.org/",
        version="6.18.0 (vendored)",
        used_for="Vector map renderer. No Mapbox account, token or telemetry.",
        attribution="MapLibre GL JS (BSD-3-Clause)",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "font-fraunces": SourceRef(
        id="font-fraunces",
        title="Fraunces variable serif and Manrope sans",
        provider="Google Fonts",
        license="SIL Open Font License 1.1",
        license_url="https://openfontlicense.org/",
        url="https://fonts.google.com/",
        version="Vendored WOFF2 subsets",
        used_for="Editorial headings (Latin). System fallbacks apply.",
        attribution="Google Fonts (OFL 1.1)",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
    "font-noto-bengali": SourceRef(
        id="font-noto-bengali",
        title="Noto Sans Bengali",
        provider="Google Fonts",
        license="SIL Open Font License 1.1",
        license_url="https://openfontlicense.org/",
        url="https://fonts.google.com/noto/specimen/Noto+Sans+Bengali",
        version="Vendored WOFF2 subset",
        used_for="Bangla interface text.",
        attribution="Google Fonts (OFL 1.1)",
        retrieved_at_utc="2026-11-15T13:40:00Z",
    ),
}


def source_list(ids) -> list[SourceRef]:
    seen: set[str] = set()
    out: list[SourceRef] = []
    for sid in ids:
        if sid in seen or sid not in SOURCES:
            continue
        seen.add(sid)
        out.append(SOURCES[sid])
    return out


# --------------------------------------------------------------------------- #
# layers
# --------------------------------------------------------------------------- #
def _legend(kind, unit, native, temporal, stops=None, classes=None, note=None, scale_note=None) -> Legend:
    return Legend(
        kind=kind,
        unit=unit,
        native_resolution=native,
        temporal=temporal,
        stops=[LegendStop(value=v, color=c, label=label) for v, c, label in (stops or [])],
        classes=classes or [],
        note=note,
        scale_note=scale_note,
    )


def _vector_layer(
    *,
    id: str,
    title: str,
    title_bn: str,
    variable: str,
    native: str,
    temporal: str,
    source_id: str,
    license: str,
    attribution: str,
    caveat: str,
    geometry_file: str,
    unit: str = "",
    group: str = "boundaries",
) -> Layer:
    return Layer(
        id=id,
        title=title,
        title_bn=title_bn,
        group=group,
        kind="vector",
        variable=variable,
        units=unit,
        native_resolution=native,
        temporal_resolution=temporal,
        aggregation="administrative polygon (no aggregation)",
        data_type="published_reference",
        mode="offline",
        attribution=attribution,
        license=license,
        source_id=source_id,
        caveat=caveat,
        legend=_legend("vector", unit or "boundary", native, temporal, note=caveat),
        geometry_file=geometry_file,
    )


BOUNDARY_LAYERS: dict[str, Layer] = {
    "world-countries": _vector_layer(
        id="world-countries",
        title="Countries",
        title_bn="দেশ",
        variable="Country boundary",
        native="1:50m cartographic outline (Natural Earth 5.1.2)",
        temporal="Natural Earth 5.1.2",
        source_id="naturalearth-50m-countries",
        license="Public Domain",
        attribution="Natural Earth (public domain)",
        caveat="Cartographic outline for orientation; not a legal or cadastral boundary.",
        geometry_file="world_countries.geojson",
    ),
    "bd-adm1": _vector_layer(
        id="bd-adm1",
        title="Divisions",
        title_bn="বিভাগ",
        variable="Administrative division",
        native="geoBoundaries BGD ADM1 (2015), simplified source release",
        temporal="2015 boundary release",
        source_id="geoboundaries-BGD-ADM1",
        license="CC0 1.0 Universal",
        attribution="geoBoundaries (CC0)",
        caveat="Administrative boundary, not an agro-ecological or soil zone.",
        geometry_file="bd_adm1.geojson",
    ),
    "bd-adm2": _vector_layer(
        id="bd-adm2",
        title="Districts",
        title_bn="জেলা",
        variable="Administrative district",
        native="geoBoundaries BGD ADM2 (2020), simplified source release",
        temporal="2020 boundary release",
        source_id="geoboundaries-BGD-ADM2",
        license="CC BY 3.0 IGO",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
        caveat="Administrative boundary. Pilot extents are district unions, not physiographic boundaries.",
        geometry_file="bd_adm2.geojson",
    ),
    "bd-adm3": _vector_layer(
        id="bd-adm3",
        title="Upazilas / thanas",
        title_bn="উপজেলা / থানা",
        variable="Administrative upazila or metropolitan thana",
        native="geoBoundaries BGD ADM3 (2020); display simplified to ~130 m tolerance",
        temporal="2020 boundary release (544 polygons)",
        source_id="geoboundaries-BGD-ADM3",
        license="CC BY 3.0 IGO",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
        caveat=(
            "544 polygons include metropolitan thanas, so counts differ from the 495-upazila list. "
            "Display geometry is Douglas-Peucker simplified (~130 m) and is never cadastral."
        ),
        geometry_file="bd_adm3.geojson",
    ),
    "us-adm1": _vector_layer(
        id="us-adm1",
        title="US states",
        title_bn="মার্কিন অঙ্গরাজ্য",
        variable="State boundary",
        native="US Census TIGER cartographic boundary, via geoBoundaries (2018)",
        temporal="2018 boundary release",
        source_id="geoboundaries-USA-ADM1",
        license="Public Domain",
        attribution="US Census Bureau (public domain) via geoBoundaries",
        caveat="Cartographic boundary, not a survey or legal description.",
        geometry_file="us_adm1.geojson",
    ),
    "us-ia-adm2": _vector_layer(
        id="us-ia-adm2",
        title="Iowa counties",
        title_bn="আইওয়া কাউন্টি",
        variable="County boundary",
        native="US Census TIGER cartographic boundary, via geoBoundaries (2018)",
        temporal="2018 boundary release",
        source_id="geoboundaries-USA-ADM2",
        license="Public Domain",
        attribution="US Census Bureau (public domain) via geoBoundaries",
        caveat="County boundary; no parcel or field boundary is bundled.",
        geometry_file="us_ia_adm2.geojson",
    ),
    "pilot-barind": _vector_layer(
        id="pilot-barind",
        title="Barind pilot extent (8 districts)",
        title_bn="বরেন্দ্র পাইলট (৮ জেলা)",
        variable="Operational pilot extent (administrative proxy)",
        native="Union of 8 Rajshahi Division districts (BBS/OCHA 2020)",
        temporal="2020 district boundaries",
        source_id="geoboundaries-BGD-ADM2",
        license="CC BY 3.0 IGO",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
        caveat=(
            "Administrative proxy only. The physiographic Barind Tract (~7,770 km2) extends into "
            "Dinajpur/Rangpur and excludes floodplain margins of these districts."
        ),
        geometry_file="bd_adm2.geojson",
        group="pilot",
    ),
    "pilot-coastal": _vector_layer(
        id="pilot-coastal",
        title="Coastal pilot extent (19 districts)",
        title_bn="উপকূলীয় পাইলট (১৯ জেলা)",
        variable="Operational coastal extent (administrative proxy)",
        native="Union of 19 WARPO/World Bank (2014) coastal districts",
        temporal="2020 district boundaries",
        source_id="geoboundaries-BGD-ADM2",
        license="CC BY 3.0 IGO",
        attribution="BBS / OCHA ROAP via geoBoundaries (CC BY 3.0 IGO)",
        caveat=(
            "Administrative proxy only. Salinity, surge and tidal exposure vary within and between "
            "these districts and require dated local evidence."
        ),
        geometry_file="bd_adm2.geojson",
        group="pilot",
    ),
}


def _gibs_layer(
    *,
    id: str,
    title: str,
    title_bn: str,
    group: str,
    variable: str,
    units: str,
    native: str,
    temporal: str,
    aggregation: str,
    data_type: str,
    source_id: str,
    gibs_layer: str,
    matrix_level: int,
    caveat: str,
    stops,
    note: str,
    date_offset_days: int,
    scale_note: str | None = None,
) -> Layer:
    return Layer(
        id=id,
        title=title,
        title_bn=title_bn,
        group=group,
        kind="raster",
        variable=variable,
        units=units,
        native_resolution=native,
        temporal_resolution=temporal,
        aggregation=aggregation,
        data_type=data_type,
        mode="online",
        attribution=f"NASA GIBS / {title}",
        license="NASA open data",
        source_id=source_id,
        caveat=caveat,
        legend=_legend(
            "gradient",
            units,
            native,
            temporal,
            stops=stops,
            note=note,
            scale_note=scale_note,
        ),
        gibs_layer=gibs_layer,
        matrix_set=f"GoogleMapsCompatible_Level{matrix_level}",
        matrix_level=matrix_level,
        date_offset_days=date_offset_days,
    )


RASTER_LAYERS: dict[str, Layer] = {
    "imerg-precip": _gibs_layer(
        id="imerg-precip",
        title="Precipitation rate (IMERG)",
        title_bn="বৃষ্টিপাতের হার (IMERG)",
        group="water",
        variable="Surface precipitation rate",
        units="mm h⁻¹",
        native="0.1° × 0.1° grid (~11 km N–S at 24°N)",
        temporal="Daily composite, about 1 day behind real time",
        aggregation="Daily rate field; GIBS serves the daily composite",
        data_type="observed",
        source_id="nasa-gpm-imerg",
        gibs_layer="IMERG_Precipitation_Rate",
        matrix_level=6,
        caveat=(
            "Satellite precipitation retrieval at ~11 km. It is not rain-gauge data and cannot "
            "resolve a field. GIBS serves it on a global zoom-6 tile matrix, so screen sharpness "
            "is not the data resolution."
        ),
        stops=[
            (0.1, "#00764e", "0.1"),
            (0.5, "#45c000", "0.5"),
            (1, "#c3e400", "1"),
            (2, "#ffb006", "2"),
            (5, "#ff4730", "5"),
            (10, "#e70000", "10"),
            (20, "#9c0000", "20"),
            (50, "#3f0000", "50+"),
        ],
        note="Palette sampled from the GIBS IMERG colour map; below 0.1 mm h⁻¹ is transparent.",
        date_offset_days=2,
    ),
    "smap-rootzone": _gibs_layer(
        id="smap-rootzone",
        title="Root-zone soil moisture (SMAP L4)",
        title_bn="মূল অঞ্চলের মাটি-আর্দ্রতা (SMAP L4)",
        group="soil",
        variable="Modeled root-zone soil moisture, 0–100 cm",
        units="m³ m⁻³",
        native="9 km EASE-Grid 2.0 output; SMAP radiometer footprint ≈36 km",
        temporal="Daily, 12z instantaneous model value-added product; several days latency",
        aggregation="Land-surface model assimilation, not a direct farm measurement",
        data_type="model_estimate",
        source_id="nasa-smap-l4",
        gibs_layer="SMAP_L4_Analyzed_Root_Zone_Soil_Moisture",
        matrix_level=6,
        caveat=(
            "This is a MODEL VALUE-ADDED assimilation product on a 9 km grid. The satellite "
            "radiometer footprint is about 36 km. It is never a measurement of an individual farm, "
            "and its display tiles are coarser than the 9 km grid."
        ),
        stops=[
            (0.05, "#ffcd00", "0.05"),
            (0.10, "#fff800", "0.10"),
            (0.15, "#b8db00", "0.15"),
            (0.20, "#4da600", "0.20"),
            (0.25, "#008f1f", "0.25"),
            (0.30, "#00ca95", "0.30"),
            (0.40, "#009aff", "0.40"),
            (0.50, "#0000db", "0.50"),
            (0.60, "#060664", "0.60+"),
        ],
        note="Palette sampled from the GIBS SMAP colour map. Volumetric water content, not plant-available water.",
        date_offset_days=6,
    ),
    "modis-ndvi": _gibs_layer(
        id="modis-ndvi",
        title="Vegetation greenness (NDVI, 8-day)",
        title_bn="উদ্ভিদ সবুজতা (NDVI, ৮ দিন)",
        group="vegetation",
        variable="Normalized Difference Vegetation Index",
        units="index (−1 to 1)",
        native="250 m",
        temporal="Rolling 8-day composite, updated daily",
        aggregation="Maximum-value composite",
        data_type="observed",
        source_id="nasa-modis-ndvi",
        gibs_layer="MODIS_Terra_NDVI_8Day",
        matrix_level=9,
        caveat=(
            "Greenness index at 250 m. Cloud, haze and compositing affect it; it is not a crop "
            "classification, yield estimate or stress diagnosis."
        ),
        stops=[
            (-0.1, "#e1e1e1", "−0.1"),
            (0.1, "#dfcec2", "0.1"),
            (0.2, "#b09b8a", "0.2"),
            (0.3, "#965a47", "0.3"),
            (0.4, "#8fb716", "0.4"),
            (0.5, "#56a100", "0.5"),
            (0.6, "#3e8a01", "0.6"),
            (0.8, "#086701", "0.8+"),
        ],
        note="Palette sampled from the GIBS NDVI colour map.",
        date_offset_days=16,
    ),
    "hls-l30": _gibs_layer(
        id="hls-l30",
        title="Surface reflectance (HLS Landsat)",
        title_bn="ভূপৃষ্ঠ প্রতিফলন (HLS Landsat)",
        group="imagery",
        variable="Nadir BRDF-adjusted surface reflectance",
        units="reflectance (0–1)",
        native="30 m",
        temporal="Best available ~daily; cloud-dependent, several days latency",
        aggregation="Per-scene reflectance, no temporal composite",
        data_type="observed",
        source_id="nasa-hls",
        gibs_layer="HLS_L30_Nadir_BRDF_Adjusted_Reflectance",
        matrix_level=12,
        caveat=(
            "30 m reflectance, but a 30 m pixel is still not a field measurement. Clouds, shadows "
            "and the fixed display date can make a tile blank; choose another date."
        ),
        stops=[
            (0.0, "#101010", "0.0"),
            (0.1, "#3b3b3b", "0.1"),
            (0.2, "#6f6f6f", "0.2"),
            (0.3, "#a0a0a0", "0.3"),
            (0.4, "#cfcfcf", "0.4"),
            (0.6, "#ffffff", "0.6+"),
        ],
        note="Greyscale reference for the RGB reflectance composite; bands are not a single variable.",
        date_offset_days=10,
        scale_note="GIBS returns a three-band RGB reflectance image. This greyscale scale is an orientation aid only.",
    ),
    "hls-s30": _gibs_layer(
        id="hls-s30",
        title="Surface reflectance (HLS Sentinel-2)",
        title_bn="ভূপৃষ্ঠ প্রতিফলন (HLS Sentinel-2)",
        group="imagery",
        variable="Nadir BRDF-adjusted surface reflectance",
        units="reflectance (0–1)",
        native="30 m",
        temporal="Best available ~5-day revisit; cloud-dependent",
        aggregation="Per-scene reflectance, no temporal composite",
        data_type="observed",
        source_id="nasa-hls",
        gibs_layer="HLS_S30_Nadir_BRDF_Adjusted_Reflectance",
        matrix_level=12,
        caveat=(
            "30 m reflectance from Sentinel-2 MSI. Clouds and shadows are common in the monsoon; "
            "a blank tile means no usable observation for that date."
        ),
        stops=[
            (0.0, "#101010", "0.0"),
            (0.1, "#3b3b3b", "0.1"),
            (0.2, "#6f6f6f", "0.2"),
            (0.3, "#a0a0a0", "0.3"),
            (0.4, "#cfcfcf", "0.4"),
            (0.6, "#ffffff", "0.6+"),
        ],
        note="Greyscale reference for the RGB reflectance composite; bands are not a single variable.",
        date_offset_days=10,
        scale_note="GIBS returns a three-band RGB reflectance image. This greyscale scale is an orientation aid only.",
    ),
    "srtm-elevation": _gibs_layer(
        id="srtm-elevation",
        title="Elevation (SRTM)",
        title_bn="উচ্চতা (SRTM)",
        group="terrain",
        variable="Terrain elevation above sea level",
        units="m",
        native="30 m (1 arc-second)",
        temporal="Static: STS-99 mission, February 2000",
        aggregation="None; void-filled DEM",
        data_type="observed",
        source_id="nasa-srtm",
        gibs_layer="SRTM_Color_Index",
        matrix_level=12,
        caveat=(
            "Year-2000 elevation. It does not show current land use, embankments, excavation or "
            "subsidence. Vertical accuracy is metres, not centimetres."
        ),
        stops=[
            (0, "#007527", "0"),
            (100, "#008c36", "100"),
            (300, "#0fb348", "300"),
            (600, "#7bce22", "600"),
            (1000, "#c4d50b", "1000"),
            (2000, "#cca00e", "2000"),
            (3000, "#ad5c30", "3000"),
            (5000, "#b9b9b9", "5000+"),
        ],
        note="Palette sampled from the GIBS SRTM colour map; static layer, no date selector.",
        date_offset_days=0,
    ),
    "modis-truecolor": _gibs_layer(
        id="modis-truecolor",
        title="True colour imagery (MODIS)",
        title_bn="প্রকৃত রঙের চিত্র (MODIS)",
        group="imagery",
        variable="Corrected reflectance RGB",
        units="RGB composite",
        native="250 m",
        temporal="Daily",
        aggregation="Daily browse image",
        data_type="observed",
        source_id="nasa-modis-truecolor",
        gibs_layer="MODIS_Terra_CorrectedReflectance_TrueColor",
        matrix_level=9,
        caveat="Visual context only. Clouds, smoke and haze are common; not an analysis layer.",
        stops=[
            (0, "#f5f3eb", "bright surface"),
            (1, "#8aa38d", "mixed"),
            (2, "#2f5d4a", "vegetated"),
            (3, "#16324a", "water/shadow"),
        ],
        note="No quantitative scale: the layer is a three-band RGB image.",
        date_offset_days=1,
    ),
}

CLIMATE_GRID_LAYER = Layer(
    id="power-grid",
    title="Climate grid (NASA POWER)",
    title_bn="জলবায়ু গ্রিড (NASA POWER)",
    group="climate_grid",
    kind="grid",
    variable="Grid-cell outline for POWER meteorology and solar cells",
    units="cell outline (no values drawn)",
    native_resolution="0.5° × 0.625° meteorology; 1° × 1° solar",
    temporal_resolution="Daily/monthly API series (retrieved by EarthSync)",
    aggregation="Cell-centred reanalysis; no farm interpolation",
    data_type="reanalysis",
    mode="offline",
    attribution="NASA POWER / MERRA-2 / CERES",
    license="NASA open data",
    source_id="nasa-power",
    caveat=(
        "The drawn cell is the native POWER support. A 0.5° × 0.625° cell is about 55 × 63 km "
        "at 24°N. Values from this cell are never a farm measurement."
    ),
    legend=_legend(
        "vector",
        "cell outline",
        "0.5° × 0.625° met / 1° × 1° solar",
        "daily/monthly series",
        note="Grid edges are computed from the POWER cell-centre convention, not sampled from a raster.",
    ),
)


def boundary_layers_for(country_code: str | None) -> list[Layer]:
    out = [BOUNDARY_LAYERS["world-countries"]]
    if country_code == "BD":
        out += [
            BOUNDARY_LAYERS["bd-adm1"],
            BOUNDARY_LAYERS["bd-adm2"],
            BOUNDARY_LAYERS["bd-adm3"],
            BOUNDARY_LAYERS["pilot-barind"],
            BOUNDARY_LAYERS["pilot-coastal"],
        ]
    elif country_code == "US":
        out += [BOUNDARY_LAYERS["us-adm1"], BOUNDARY_LAYERS["us-ia-adm2"]]
    return out


def raster_layers() -> list[Layer]:
    return list(RASTER_LAYERS.values())


def all_layers(country_code: str | None = None) -> list[Layer]:
    return boundary_layers_for(country_code) + raster_layers() + [CLIMATE_GRID_LAYER]


# --------------------------------------------------------------------------- #
# datasets (what analysis may consume, and under which gate)
# --------------------------------------------------------------------------- #
def _dataset(
    *,
    id: str,
    name: str,
    provider: str,
    source_id: str,
    license: str,
    status: Availability,
    readiness: Readiness,
    native: str,
    footprint: str | None,
    temporal: str,
    aggregation: str,
    data_type: str,
    layer_ids: list[str],
    access: str,
    caveat: str,
) -> DatasetAvailability:
    return DatasetAvailability(
        id=id,
        name=name,
        provider=provider,
        source_id=source_id,
        license=license,
        status=status,
        readiness=readiness,
        native_resolution=native,
        footprint_km=footprint,
        temporal_resolution=temporal,
        aggregation=aggregation,
        data_type=data_type,
        layer_ids=layer_ids,
        access=access,
        caveat=caveat,
        is_field_measurement=False,
    )


POWER_DATASET = _dataset(
    id="power-climate",
    name="NASA POWER climate series",
    provider="NASA POWER (MERRA-2 / CERES)",
    source_id="nasa-power",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="0.5° × 0.625° meteorology; 1° × 1° solar",
    footprint="~55 × 63 km met cell at 24°N",
    temporal="Daily and monthly series, 1981–present",
    aggregation="Area-average reanalysis for the grid cell",
    data_type="reanalysis",
    layer_ids=["power-grid"],
    access="EarthSync getEnvironmentalSeries (external service)",
    caveat="Gridded reanalysis, not a farm measurement. Retrieval is owned by EarthSync; this router only advertises access.",
)

IMERG_DATASET = _dataset(
    id="gpm-imerg",
    name="GPM IMERG precipitation",
    provider="NASA GPM",
    source_id="nasa-gpm-imerg",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="0.1° × 0.1° (~11 km)",
    footprint="~11 × 11 km per grid cell at 24°N",
    temporal="Daily composite; half-hourly product available upstream",
    aggregation="Satellite multi-sensor retrieval",
    data_type="observed",
    layer_ids=["imerg-precip"],
    access="NASA GIBS WMTS tiles (display); series retrieval via EarthSync",
    caveat="Satellite-retrieved precipitation at ~11 km; not a rain gauge and not field rainfall.",
)

SMAP_DATASET = _dataset(
    id="smap-l4-rootzone",
    name="SMAP L4 root-zone soil moisture",
    provider="NASA SMAP / NSIDC",
    source_id="nasa-smap-l4",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="9 km EASE-Grid 2.0 output",
    footprint="≈36 km radiometer footprint assimilated into a 9 km model grid",
    temporal="Daily 12z instantaneous, model value-added",
    aggregation="Land-surface model assimilation",
    data_type="model_estimate",
    layer_ids=["smap-rootzone"],
    access="NASA GIBS WMTS tiles (display); series retrieval via EarthSync",
    caveat="Modeled root-zone moisture on a 9 km grid with a ~36 km source footprint. Never an individual farm reading.",
)

NDVI_DATASET = _dataset(
    id="modis-ndvi-8day",
    name="MODIS NDVI (rolling 8-day)",
    provider="NASA MODIS",
    source_id="nasa-modis-ndvi",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="250 m",
    footprint="250 m pixel",
    temporal="8-day rolling composite",
    aggregation="Maximum-value composite",
    data_type="observed",
    layer_ids=["modis-ndvi"],
    access="NASA GIBS WMTS tiles (display)",
    caveat="Greenness at 250 m; not a crop map, yield estimate or stress diagnosis.",
)

HLS_DATASET = _dataset(
    id="hls-30m",
    name="HLS 30 m surface reflectance",
    provider="NASA HLS",
    source_id="nasa-hls",
    license="NASA open data",
    status=Availability.CONDITIONAL,
    readiness=Readiness.CONDITIONAL,
    native="30 m",
    footprint="30 m pixel",
    temporal="Best available per scene; cloud-dependent",
    aggregation="Per-scene nadir BRDF-adjusted reflectance",
    data_type="observed",
    layer_ids=["hls-l30", "hls-s30"],
    access="NASA GIBS WMTS tiles (display)",
    caveat="30 m is finer than any other layer here, but a 30 m pixel is still not a field measurement, and monsoon cloud can remove useful dates.",
)

SRTM_DATASET = _dataset(
    id="srtm-elevation",
    name="SRTM elevation",
    provider="NASA / NGA",
    source_id="nasa-srtm",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.EXPLORATION,
    native="30 m",
    footprint="30 m pixel",
    temporal="Static (2000)",
    aggregation="Void-filled DEM",
    data_type="observed",
    layer_ids=["srtm-elevation"],
    access="NASA GIBS WMTS tiles (display)",
    caveat="Year-2000 terrain context; does not show current embankments or subsidence.",
)

TRUECOLOR_DATASET = _dataset(
    id="modis-truecolor",
    name="MODIS true colour",
    provider="NASA MODIS",
    source_id="nasa-modis-truecolor",
    license="NASA open data",
    status=Availability.AVAILABLE,
    readiness=Readiness.EXPLORATION,
    native="250 m",
    footprint="250 m pixel",
    temporal="Daily",
    aggregation="Daily browse composite",
    data_type="observed",
    layer_ids=["modis-truecolor"],
    access="NASA GIBS WMTS tiles (display)",
    caveat="Visual context only; not an analysis layer.",
)

BD_BOUNDARY_DATASET = _dataset(
    id="bd-administrative-boundaries",
    name="Bangladesh administrative boundaries",
    provider="BBS / OCHA ROAP via geoBoundaries",
    source_id="geoboundaries-BGD-ADM3",
    license="CC0 (ADM0/1) and CC BY 3.0 IGO (ADM2/3)",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="Division, district, upazila/thana polygons; ADM3 display simplified ~130 m",
    footprint=None,
    temporal="ADM1 2015; ADM2/ADM3 2020 release",
    aggregation="Administrative units",
    data_type="published_reference",
    layer_ids=["bd-adm1", "bd-adm2", "bd-adm3"],
    access="Offline bundle (bundled GeoJSON)",
    caveat="Administrative units are not soil, agro-ecological or cadastral boundaries. ADM3 has 544 polygons incl. metropolitan thanas.",
)

US_BOUNDARY_DATASET = _dataset(
    id="us-administrative-boundaries",
    name="US state and Iowa county boundaries",
    provider="US Census Bureau via geoBoundaries",
    source_id="geoboundaries-USA-ADM2",
    license="Public Domain",
    status=Availability.AVAILABLE,
    readiness=Readiness.CONDITIONAL,
    native="State and county cartographic boundaries (2018)",
    footprint=None,
    temporal="2018 release",
    aggregation="Administrative units",
    data_type="published_reference",
    layer_ids=["us-adm1", "us-ia-adm2"],
    access="Offline bundle (bundled GeoJSON)",
    caveat="Cartographic boundaries; no parcel or field boundary is bundled.",
)

GLOBAL_BOUNDARY_DATASET = _dataset(
    id="country-boundaries",
    name="Natural Earth country outlines",
    provider="Natural Earth",
    source_id="naturalearth-50m-countries",
    license="Public Domain",
    status=Availability.AVAILABLE,
    readiness=Readiness.EXPLORATION,
    native="1:50m cartographic outline",
    footprint=None,
    temporal="Natural Earth 5.1.2",
    aggregation="Country units",
    data_type="published_reference",
    layer_ids=["world-countries"],
    access="Offline bundle (bundled GeoJSON)",
    caveat="Cartographic outline for orientation; not a legal boundary.",
)


def datasets_for(country_code: str | None) -> list[DatasetAvailability]:
    out = [
        POWER_DATASET,
        IMERG_DATASET,
        SMAP_DATASET,
        NDVI_DATASET,
        HLS_DATASET,
        TRUECOLOR_DATASET,
        SRTM_DATASET,
    ]
    if country_code == "BD":
        out.insert(0, BD_BOUNDARY_DATASET)
    elif country_code == "US":
        out.insert(0, US_BOUNDARY_DATASET)
    else:
        out.insert(0, GLOBAL_BOUNDARY_DATASET)
    return out


# --------------------------------------------------------------------------- #
# region packs
# --------------------------------------------------------------------------- #
REGION_PACKS: dict[str, dict] = {
    "BD-NATIONAL": {
        "regionId": "BD-NATIONAL",
        "label": "Bangladesh · national context",
        "labelBn": "বাংলাদেশ · জাতীয় প্রেক্ষাপট",
        "mode": "conditional",
        "readinessCap": Readiness.CONDITIONAL,
        "packStatus": "national_context_only",
        "extentBasis": "Country and administrative units only; no soil or agro-ecological zone is bundled.",
        "description": (
            "National Bangladesh context with division → district → upazila browsing where boundary "
            "data exists. Environmental layers are NASA gridded products; the router never upgrades "
            "them to field evidence."
        ),
        "limitations": [
            "No field measurements: every environmental layer is gridded, modeled or satellite-retrieved.",
            "Upazila polygons follow the 2020 BBS/OCHA 544-polygon file and include metropolitan thanas; they are not cadastral and differ from the 495-upazila list.",
            "Crop suitability and rotation rules are owned by SoilBrain and are not duplicated in this router.",
            "NASA POWER and SMAP grid cells cannot be interpreted as farm-level measurements.",
        ],
        "parentRegionId": None,
    },
    "BD-RAJ-BARIND": {
        "regionId": "BD-RAJ-BARIND",
        "label": "Barind pilot · Rajshahi Division",
        "labelBn": "বরেন্দ্র পাইলট · রাজশাহী বিভাগ",
        "mode": "research_pilot",
        "readinessCap": Readiness.RESEARCH_PILOT,
        "packStatus": "admin_proxy_pilot",
        "extentBasis": (
            "Administrative proxy: the 8 Rajshahi Division districts of Rajshahi, Chapainawabganj, "
            "Naogaon, Natore, Pabna, Sirajganj, Bogura and Joypurhat. The physiographic Barind Tract "
            "(~7,770 km2) is smaller and extends into Dinajpur/Rangpur."
        ),
        "description": (
            "The deep Bangladesh pilot: district-level browsing, research-pilot water and rotation "
            "status, and explicit limits. The extent is administrative, so it overstates the "
            "physiographic tract and includes floodplain margins."
        ),
        "limitations": [
            "Pilot extent is an administrative proxy (~18,268 km2 of districts), not the ~7,770 km2 physiographic Barind Tract.",
            "Upazila polygons follow the 2020 BBS/OCHA 544-polygon file and include metropolitan thanas; they are not cadastral and differ from the 495-upazila list.",
            "Water and rotation gates are research_pilot, meaning a documented pilot configuration — not validated farm accuracy.",
            "NASA POWER/IMERG/SMAP cells are regional and cannot measure a farm.",
            "No field soil test, no verified local prices or costs, and no fabricated validation.",
        ],
        "parentRegionId": "BD-NATIONAL",
    },
    "BD-COASTAL": {
        "regionId": "BD-COASTAL",
        "label": "Coastal Bangladesh · salinity-gated",
        "labelBn": "উপকূলীয় বাংলাদেশ · লবণাক্ততা-শর্তাধীন",
        "mode": "conditional",
        "readinessCap": Readiness.CONDITIONAL,
        "packStatus": "conditional_pilot",
        "extentBasis": "19 coastal districts per WARPO / World Bank (2014).",
        "description": (
            "Coastal Bangladesh is selectable, but soil and water analyses stay conditional until a "
            "dated local salinity measurement exists. Tidal exposure, storm surge and salinity vary "
            "within a single district."
        ),
        "limitations": [
            "Satellite and gridded climate data cannot replace a dated soil or irrigation-water salinity measurement.",
            "The 19-district extent is administrative; salinity is not uniform inside it.",
            "Coastal polders, embankments and drainage are not represented in any bundled layer.",
            "No fabricated field validation is attached to this pack.",
        ],
        "parentRegionId": "BD-NATIONAL",
    },
    "US-IA-STORY": {
        "regionId": "US-IA-STORY",
        "label": "Story County, Iowa · research pilot",
        "labelBn": "স্টোরি কাউন্টি, আইওয়া · গবেষণা পাইলট",
        "mode": "research_pilot",
        "readinessCap": Readiness.RESEARCH_PILOT,
        "packStatus": "us_research_pilot",
        "extentBasis": "Story County, Iowa (US Census TIGER 2018), inside the Iowa state pilot frame.",
        "description": (
            "The single US research pilot. Geography and NASA context are available; USDA soil and "
            "crop evidence is advertised as an integration requirement, not claimed as present."
        ),
        "limitations": [
            "The US pilot uses its own regional references and never supplies attributes to Bangladesh farms.",
            "USDA soil and crop layers are not integrated in this module; county soil properties remain unknown here.",
            "County boundaries are cartographic, not survey or parcel boundaries.",
            "NASA gridded products retain their native footprint and are not farm measurements.",
        ],
        "parentRegionId": "US-IA",
    },
    "US-IA": {
        "regionId": "US-IA",
        "label": "Iowa · pilot state context",
        "labelBn": "আইওয়া · পাইলট রাজ্য",
        "mode": "conditional",
        "readinessCap": Readiness.CONDITIONAL,
        "packStatus": "pilot_state_context",
        "extentBasis": "Iowa state boundary (US Census TIGER 2018).",
        "description": "Iowa context outside Story County: county browsing is available; the research-pilot gate is not.",
        "limitations": [
            "Outside Story County, no US research pilot is claimed.",
            "USDA soil/crop integration is absent, so soil and economics remain conditional.",
            "County boundaries are cartographic, not survey boundaries.",
        ],
        "parentRegionId": "US-NATIONAL",
    },
    "US-NATIONAL": {
        "regionId": "US-NATIONAL",
        "label": "United States · exploration",
        "labelBn": "মার্কিন যুক্তরাষ্ট্র · অন্বেষণ",
        "mode": "exploration",
        "readinessCap": Readiness.EXPLORATION,
        "packStatus": "no_pack",
        "extentBasis": "State outlines only; the single research pilot is Story County, Iowa.",
        "description": "US exploration outside Iowa: state context and global NASA layers, without a regional pack.",
        "limitations": [
            "No US region pack exists outside the Iowa pilot.",
            "USDA integration would be required before any soil or economics claim.",
            "State outlines are cartographic, not legal descriptions.",
        ],
        "parentRegionId": None,
    },
    "GLOBAL": {
        "regionId": "GLOBAL",
        "label": "Global explorer",
        "labelBn": "বৈশ্বিক অন্বেষণ",
        "mode": "exploration",
        "readinessCap": Readiness.EXPLORATION,
        "packStatus": "no_pack",
        "extentBasis": "Natural Earth country outlines and global NASA gridded products.",
        "description": (
            "Location search and global climate context. No local crop calendar, soil constraint, "
            "price basis or field evidence is bundled, so the router refuses farm-level claims and "
            "returns typed missing requirements instead."
        ),
        "limitations": [
            "Global environmental access does not establish locally validated farm recommendations.",
            "No local crop calendar, soil constraints or price/cost basis are bundled for this country.",
            "Country outlines are cartographic; no sub-national boundary is bundled outside Bangladesh and the US pilot.",
            "Every analysis above climate context is refused rather than guessed.",
        ],
        "parentRegionId": None,
    },
}


def region_pack(region_id: str) -> dict:
    return REGION_PACKS.get(region_id, REGION_PACKS["GLOBAL"])


# --------------------------------------------------------------------------- #
# analysis gates
# --------------------------------------------------------------------------- #
def _gate(analysis, status, readiness, reasons, missing, datasets, owner) -> AnalysisGate:
    return AnalysisGate(
        analysis=analysis,
        status=status,
        readiness=readiness,
        reasons=reasons,
        missing=missing,
        datasets=datasets,
        owner=owner,
    )


def analysis_gates(region_id: str, admin_depth: int) -> dict[str, AnalysisGate]:
    """Readiness per analysis. No gate may exceed its region pack's cap."""

    climate_reason = (
        "NASA POWER provides a 0.5° × 0.625° reanalysis cell (1° × 1° solar); it is regional context, "
        "not a farm observation."
    )
    gates: dict[str, AnalysisGate] = {}

    if region_id == "BD-RAJ-BARIND":
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["No field soil test is bundled; SoilBrain owns crop and soil rules."], ["field_soil_measurement", "soil_profile_from_SoilBrain"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.AVAILABLE, Readiness.RESEARCH_PILOT, ["Pilot configuration documented; gridded water balance is research-grade, not validated on farms."], ["field_scale_water_balance_evidence"], ["power-climate", "gpm-imerg", "smap-l4-rootzone"], "EarthSync")
        gates["rotation"] = _gate("rotation", Availability.AVAILABLE, Readiness.RESEARCH_PILOT, ["Rotation comparison is a research-pilot capability; crop rules are not stored here."], ["verified_local_prices_and_costs", "local_crop_calendar"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["Local price and cost basis is absent."], ["verified_local_prices_and_costs"], [], "FutureFields")
    elif region_id == "BD-COASTAL":
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.BLOCKED, Readiness.CONDITIONAL, ["Coastal soil interpretation is blocked until salinity status is known."], ["dated_soil_or_irrigation_water_salinity", "field_soil_measurement"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.CONDITIONAL, Readiness.CONDITIONAL, ["Tidal and salinity processes are not represented by POWER or SMAP; local evidence is required."], ["dated_salinity_measurement", "local_drainage_evidence"], ["power-climate", "gpm-imerg", "smap-l4-rootzone"], "AquaSense")
        gates["rotation"] = _gate("rotation", Availability.CONDITIONAL, Readiness.CONDITIONAL, ["Salinity-gated soils make rotation advice conditional."], ["local_crop_calendar", "salinity_status"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["Local price and cost basis is absent."], ["verified_local_prices_and_costs"], [], "FutureFields")
    elif region_id == "US-IA-STORY":
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["USDA soil properties are an integration requirement and are not bundled."], ["integrated_usda_soil_evidence", "field_soil_measurement"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.CONDITIONAL, Readiness.CONDITIONAL, ["Gridded water context only; no field water balance is validated."], ["field_scale_water_balance_evidence"], ["power-climate", "gpm-imerg", "smap-l4-rootzone"], "AquaSense")
        gates["rotation"] = _gate("rotation", Availability.AVAILABLE, Readiness.RESEARCH_PILOT, ["Research-pilot rotation comparison; crop rules come from SoilBrain."], ["verified_local_prices_and_costs"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["Local price and cost basis is absent."], ["verified_local_prices_and_costs"], [], "FutureFields")
    elif region_id in ("US-IA", "US-NATIONAL"):
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.BLOCKED, Readiness.EXPLORATION, ["No US soil integration outside the Story County pilot."], ["integrated_usda_soil_evidence"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["Gridded context only; no US water analysis is scoped here."], ["local_water_analysis_pack"], ["power-climate", "gpm-imerg"], "AquaSense")
        gates["rotation"] = _gate("rotation", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["Rotation rules require a US crop profile that this module does not own."], ["us_crop_profile", "verified_local_prices_and_costs"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["No US price or cost basis is bundled."], ["verified_local_prices_and_costs"], [], "FutureFields")
    elif region_id == "BD-NATIONAL":
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["Outside a pilot, soil interpretation needs a field soil test and SoilBrain's rules."], ["field_soil_measurement", "soil_profile_from_SoilBrain"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.CONDITIONAL, Readiness.CONDITIONAL, ["Gridded water context only; no national field water balance is validated."], ["local_water_analysis_pack"], ["power-climate", "gpm-imerg", "smap-l4-rootzone"], "AquaSense")
        gates["rotation"] = _gate("rotation", Availability.CONDITIONAL, Readiness.CONDITIONAL, ["Rotation needs a local crop calendar and a region pack."], ["local_crop_calendar"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.REQUIRES_INPUT, Readiness.CONDITIONAL, ["Local price and cost basis is absent."], ["verified_local_prices_and_costs"], [], "FutureFields")
    else:  # GLOBAL and any unresolved country
        gates["climate"] = _gate("climate", Availability.AVAILABLE, Readiness.CONDITIONAL, [climate_reason], [], ["power-climate", "gpm-imerg"], "EarthSync")
        gates["soil"] = _gate("soil", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["No local soil evidence or crop rules exist for this country in this module."], ["local_soil_evidence", "local_crop_calendar"], ["smap-l4-rootzone"], "SoilBrain")
        gates["water"] = _gate("water", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["Only global gridded context is available; no local water analysis is scoped."], ["local_water_analysis_pack"], ["power-climate", "gpm-imerg", "smap-l4-rootzone"], "AquaSense")
        gates["rotation"] = _gate("rotation", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["Rotation comparison requires a local crop and price profile that is not bundled."], ["local_crop_calendar", "verified_local_prices_and_costs"], [], "RootShift")
        gates["economics"] = _gate("economics", Availability.NOT_SCOPED, Readiness.EXPLORATION, ["No local price or cost basis is bundled."], ["verified_local_prices_and_costs"], [], "FutureFields")

    return gates


def clamp_readiness(gates: dict[str, AnalysisGate], cap: Readiness) -> Readiness:
    from .types import READINESS_ORDER

    cap_index = READINESS_ORDER.index(cap)
    best = Readiness.EXPLORATION
    best_index = 0
    for gate in gates.values():
        index = min(READINESS_ORDER.index(gate.readiness), cap_index)
        if index > best_index:
            best, best_index = READINESS_ORDER[index], index
    return best
