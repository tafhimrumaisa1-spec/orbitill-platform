"""SourceManifest: every organizer resource + relevant extras, with geography-specific roles.

Built from three inputs, so nothing is lost:
  1. ``data/SOURCES_RELEVANT.csv``  (supplied catalogue, 39 rows)
  2. ``data/NASA_RESOURCE_UPDATE.txt`` (organizer list, 24 named entries -> ``ORGANIZER_NAME``)
  3. curated overlay below (applicability, native resolution, access decision, license note)

Honesty fields
--------------
``verification.doc_checked``  True only when an official page was actually read during this build.
``verification.live_checked`` True only when a live request succeeded during this build (never, here:
                              the build sandbox blocked all NASA/USDA/ESA hosts).
``license.verified``          True only when the license text was read from an official page.
Everything else is flagged for verification before any public claim.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Optional

from .schemas import LicenseInfo, SourceManifestEntry

DATA_DIR = Path(__file__).resolve().parent / "data"
MANIFEST_JSON = DATA_DIR / "source_manifest.json"

# The 24 entries named in the organizer's NASA_RESOURCE_UPDATE.txt, in listed order.
ORGANIZER_NAME = {
    "NASA_SMAP": "Soil Moisture Active Passive (SMAP)",
    "NASA_GPM_IMERG": "Global Precipitation Measurement (GPM) & IMERG",
    "NASA_LANDSAT_MODIS": "Landsat and MODIS/VIIRS: Reflectance, NDVI, Vegetation Indices",
    "NASA_POWER": "NASA POWER: Agroclimatology & Meteorological Data",
    "NASA_SRTM": "Shuttle Radar Topography Mission (SRTM)",
    "NASA_ECOSTRESS": "ECOSTRESS",
    "USDA_AGCOMMONS": "USDA Ag Data Commons",
    "USDA_WSS": "Web Soil Survey (WSS)",
    "USDA_CDL": "Cropland Data Layer (CDL): CropScape",
    "PRISM": "PRISM Climate Data: Oregon State University",
    "USDA_SSURGO_STATSGO": "USDA NRCS SSURGO/STATSGO2",
    "USDA_NAIP": "National Agriculture Imagery Program (NAIP)",
    "USGS_NLCD": "USGS National Land Cover Database (NLCD)",
    "NASA_NLDAS_GLDAS": "NLDAS/GLDAS: Land Data Assimilation Systems",
    "FAO_GAEZ": "FAO Global Agro-Ecological Zones (GAEZ)",
    "COCORAHS": "CoCoRaHS: Community Rain/Snow Observations",
    "USGS_NWIS": "USGS National Water Information Systems (NWIS)",
    "USDA_AMS": "USDA AMS Market News",
    "USDA_QUICKSTATS": "USDA NASS QuickStats",
    "OPENET": "OpenET: Evapotranspiration for Water Management",
    "LANDFIRE": "USFS LANDFIRE: Vegetation & Fuel Layers",
    "NASA_GEDI": "Global Ecosystem Dynamics Investigation (GEDI)",
    "ESA_SENTINEL2": "Copernicus Sentinel-2: ESA",
    "ECMWF_ERA5": "ERA5: ECMWF Reanalysis",
}

N, L, X, M, U = "native", "limited", "not_applicable", "methodology_only", "user_supplied"


def _lic(name: str, url: Optional[str] = None, attr: Optional[str] = None, verified: bool = False, note: Optional[str] = None) -> dict:
    return dict(name=name, url=url, attribution=attr, verified=verified, note=note)


UNVERIFIED = "License text not read during this build; confirm at the provider before redistribution."

# fmt: off
# keys: pri=(bd,us,global) app=(BD,US,GLOBAL) spatial temporal latency vars auth live adapter numerical lic notes
OVERLAY: dict[str, dict] = {
    "NASA_POWER": dict(
        pri=("P0", "P0", "P0"), app=(N, N, N), kind="dataset",
        spatial="Meteorology 0.5 x 0.625 deg (MERRA-2 based); solar 1 x 1 deg; point API returns the containing cell",
        temporal="Daily (also hourly, monthly, climatology); meteorology 1981-present, radiation 1984-present",
        latency="2-7 days depending on provider; recent days revised", vars=["T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M", "PS"],
        auth="none", live="live_implemented", adapter="earthsync.adapters.nasa_power",
        lic=_lic("CC BY 4.0", "https://power.larc.nasa.gov/docs/referencing/", "NASA Langley Research Center POWER Project", True,
                 "Read from https://power.larc.nasa.gov/llms.txt during build."),
        verify=dict(doc_checked=True, doc_pages=["https://power.larc.nasa.gov/llms.txt", "https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/",
                                                  "https://power.larc.nasa.gov/docs/release-guide/", "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"],
                    live_checked=False, live_note="Egress to power.larc.nasa.gov was refused by the build sandbox policy; adapter validated against mock transport only."),
        notes=["Request at most 5 concurrent; do not request finer than native; avoid repeated requests for the same cell (official tutorial).",
               "v10.0.5 (2025-03-04) integrated IMERG v7B into POWER endpoints; exact parameter code unverified here.",
               "ALLSKY_SFC_SW_DWN unit depends on community (AG: MJ/m2/day, RE: kW-hr/m2/day): adapter reads response metadata."]),
    "NASA_POWER_PROJ": dict(
        pri=("P1_STRETCH", "P1_STRETCH", "P1_STRETCH"), app=(N, N, N), kind="dataset",
        spatial="0.25 deg (NEX-GDDP-CMIP6)", temporal="Daily, 2015-2100 scenarios (SSP)", latency=None,
        vars=["T2M", "PRECTOTCORR (projection)"], auth="none", live="manifest_only", adapter=None,
        lic=_lic("See POWER referencing page", "https://power.larc.nasa.gov/docs/referencing/", None, False, UNVERIFIED),
        verify=dict(doc_checked=False, live_checked=False),
        notes=["Scenario ensemble, not weather forecast: any use must be labelled hypothetical_scenario/forecast-class. FutureFields owns use."]),
    "NASA_GPM_IMERG": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="dataset",
        spatial="0.1 x 0.1 deg", temporal="Half-hourly rate (mm/hr); daily accumulation products; 2000-present (V07)",
        latency="Early ~4 h, Late ~12 h, Final ~3.5 months (check product page)", vars=["precipitation (mm/hr rate or mm/day accumulation)"],
        auth="earthdata_login", live="offline_extract_ingest", adapter="earthsync.adapters.imerg",
        lic=_lic("NASA Earth science open data policy", "https://gpm.nasa.gov/data/imerg", "NASA GES DISC / GPM IMERG", False, UNVERIFIED),
        verify=dict(doc_checked=False, live_checked=False),
        notes=["Rate vs accumulation: use units.rate_to_depth; never sum 48 rates.", "Run (Early/Late/Final) must be recorded; Final is gauge-calibrated.",
               "POWER also hosts IMERG (see NASA_POWER_IMERG_PARAM)."]),
    "NASA_POWER_IMERG_PARAM": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="access_service", name="IMERG via POWER endpoint (parameter unverified)", origin="New verified addition",
        spatial="0.1 deg (IMERG) delivered through POWER point API", temporal="Daily", latency="POWER-dependent", vars=["IMERG-derived precipitation"],
        auth="none", live="live_designed_untested", adapter="earthsync.adapters.nasa_power",
        lic=_lic("CC BY 4.0 (POWER) / NASA open data (IMERG)", "https://power.larc.nasa.gov/docs/referencing/", None, False, "POWER part verified; IMERG attribution to confirm."),
        verify=dict(doc_checked=True, doc_pages=["https://power.larc.nasa.gov/docs/release-guide/"], live_checked=False,
                    live_note="Release guide states IMERG v7B integrated 2025-03-04; parameter code IMERG_PRECTOT is a candidate only. 422 => typed parameter_rejected."),
        notes=["Cheapest route to a POWER-vs-IMERG cross-check without Earthdata credentials."], caveat="Parameter code, units and day boundary must be read from the response before use."),
    "NASA_SMAP": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="dataset",
        spatial="9 km EASE-Grid 2.0 (SPL3SMP_E enhanced L3); ~36 km native radiometer footprint", temporal="Daily composites (2-3 day revisit), 2015-present",
        latency="~1-3 days (check product)", vars=["soil_moisture (surface, ~0-5 cm)", "retrieval_qual_flag", "surface_flag"],
        auth="earthdata_login", live="manifest_only", adapter=None,
        lic=_lic("NASA Earth science open data policy", "https://nsidc.org/data/spl3smp_e", "NASA NSIDC DAAC", False, UNVERIFIED),
        verify=dict(doc_checked=False, live_checked=False),
        notes=["Surface soil moisture only: NOT root-zone and NOT a farm measurement. Dense vegetation and flooded paddy degrade retrievals (quality flags required).",
               "Adapter not implemented: downstream receives adapter_not_implemented, never a guessed value."]),
    "NASA_LANDSAT_MODIS": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="dataset", spatial="Landsat 30 m; MODIS 250-1000 m; VIIRS 375-750 m", temporal="Landsat 16-day; MODIS/VIIRS daily",
        latency="Days", vars=["surface reflectance", "NDVI/EVI"], auth="earthdata_login", live="manifest_only", adapter=None,
        lic=_lic("NASA/USGS open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
        notes=["Prefer HLS (harmonised Landsat+Sentinel-2) for 30 m time series; coarse MODIS for regional context only."]),
    "NASA_HLS": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="dataset", spatial="30 m (HLSL30 from Landsat 8/9, HLSS30 from Sentinel-2 resampled to 30 m)",
        temporal="2-3 day combined revisit (cloud permitting)", latency="~1.7 days nominal", vars=["B04 red", "B05/B8A NIR", "Fmask"],
        auth="earthdata_login", live="offline_extract_ingest", adapter="earthsync.adapters.hls",
        lic=_lic("NASA/LP DAAC open data", "https://lpdaac.usgs.gov/products/hlsl30v002/", None, False, UNVERIFIED),
        verify=dict(doc_checked=False, live_checked=False),
        notes=["Implemented: NDVI computation, reflectance scale factor, Fmask decoding, cloud-free gating. NDVI != yield/nutrients/disease."]),
    "ESA_SENTINEL2": dict(
        pri=("P1", "P1", "P1"), app=(N, N, N), kind="dataset", spatial="10-20 m bands (60 m atmospheric)", temporal="~5-day revisit (2 satellites)", latency="Days",
        vars=["B04", "B08", "B8A", "SCL"], auth="registration", live="manifest_only", adapter=None,
        lic=_lic("Copernicus Sentinel data terms", "https://sentinels.copernicus.eu/", "Contains modified Copernicus Sentinel data", False, UNVERIFIED),
        verify=dict(doc_checked=False, live_checked=False), notes=["Reach Sentinel-2 via NASA HLS to avoid duplicate harmonisation; HLS resamples S2 to 30 m: not new evidence."]),
    "NASA_SRTM": dict(pri=("P2", "P2", "P2"), app=(N, N, N), kind="dataset", spatial="1 arc-second (~30 m)", temporal="Static (2000)", latency=None, vars=["elevation"],
                      auth="earthdata_login", live="manifest_only", adapter=None, lic=_lic("NASA/USGS open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                      notes=["Terrain slope != flood/erosion probability. Barind is low-relief: elevation differences of metres matter and DEM vertical error is comparable."]),
    "NASA_NASADEM": dict(pri=("P2", "P2", "P2"), app=(N, N, N), kind="dataset", spatial="1 arc-second (~30 m)", temporal="Static", latency=None, vars=["elevation"],
                         auth="earthdata_login", live="manifest_only", adapter=None, lic=_lic("NASA LP DAAC open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "NASA_ECOSTRESS": dict(pri=("P2", "P2", "P2"), app=(N, N, N), kind="dataset", spatial="~70 m", temporal="Irregular ISS overpasses", latency="Days", vars=["LST", "ET (modelled)"],
                           auth="earthdata_login", live="manifest_only", adapter=None, lic=_lic("NASA LP DAAC open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "NASA_NLDAS_GLDAS": dict(pri=("P2", "P2", "P2"), app=(L, N, N), kind="dataset", spatial="NLDAS 0.125 deg (CONUS only); GLDAS 0.25 deg global", temporal="NLDAS hourly; GLDAS 3-hourly",
                             latency="Days", vars=["soil moisture layers", "ET", "forcing"], auth="earthdata_login", live="manifest_only", adapter=None,
                             lic=_lic("NASA GES DISC open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                             notes=["NLDAS does not cover Bangladesh: only GLDAS (0.25 deg) applies there."]),
    "NASA_GRACE": dict(pri=("P3", "P3", "P3"), app=(L, L, L), kind="dataset", spatial="~300 km effective", temporal="Monthly", latency="Months", vars=["terrestrial water storage anomaly"],
                       auth="earthdata_login", live="manifest_only", adapter=None, lic=_lic("NASA open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                       notes=["Cannot test individual wells; region-scale storage trend only."]),
    "NASA_GEDI": dict(pri=("P3", "P3", "P3"), app=(L, L, L), kind="dataset", spatial="25 m footprints, sparse tracks", temporal="2019-2023 mission segments", latency=None, vars=["canopy height", "biomass"],
                      auth="earthdata_login", live="manifest_only", adapter=None, lic=_lic("NASA open data", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "ECMWF_ERA5": dict(pri=("P2", "P2", "P1"), app=(N, N, N), kind="dataset", spatial="0.25 deg", temporal="Hourly, 1940-present", latency="~5 days (ERA5T)", vars=["2m temp", "precip", "radiation", "soil temp/moisture"],
                       auth="registration", live="manifest_only", adapter=None, lic=_lic("Copernicus licence", "https://cds.climate.copernicus.eu/", "Contains modified Copernicus Climate Change Service information", False, UNVERIFIED),
                       verify=dict(doc_checked=False, live_checked=False),
                       notes=["Not independent of POWER: both rest on reanalysis assimilation. Use as a second *model* view, not ground truth."]),
    "FAO_GAEZ": dict(pri=("P1", "P2", "P1"), app=(N, N, N), kind="dataset", spatial="~9 km (5 arc-min; confirm v5)", temporal="Static scenarios/periods", latency=None, vars=["suitability", "yield potential"],
                     auth="manual_download", live="manifest_only", adapter=None, lic=_lic("FAO terms (CC BY-NC-SA / CC BY - confirm)", "https://www.fao.org/gaez/en", None, False, "Non-commercial clause may apply; confirm."),
                     verify=dict(doc_checked=False, live_checked=False), notes=["Owned by Agent 05 (SoilBrain). EarthSync only exposes the registry entry."]),
    "ISRIC_SOILGRIDS": dict(pri=("P1", "P3", "P2"), app=(N, N, N), kind="dataset", spatial="250 m", temporal="Static", latency=None, vars=["sand/silt/clay", "pH", "organic carbon"],
                            auth="none", live="do_not_use_live", adapter=None, lic=_lic("CC BY 4.0", "https://docs.isric.org/globaldata/soilgrids/", "ISRIC - World Soil Information", False, UNVERIFIED),
                            verify=dict(doc_checked=False, live_checked=False, note="REST API reported paused by organizer catalogue; not verified here."),
                            notes=["Do not depend on REST. Use a pre-extracted WCS/WebDAV subset supplied by Agent 05. Modelled, not measured; no salinity."]),
    "FAO_CROP_CAL": dict(pri=("P0", "P2", "P1"), app=(N, N, N), kind="dataset", spatial="Admin-level / agro-ecological zone", temporal="Annual calendar", latency=None, vars=["planting/harvest windows"],
                         auth="manual_download", live="manifest_only", adapter=None, lic=_lic("FAO terms", "https://cropcalendar.apps.fao.org/", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                         notes=["Owned by Agent 05 (SoilBrain)."]),
    "FAO_56": dict(pri=("P0", "P0", "P0"), app=(M, M, M), kind="methodology", spatial="n/a", temporal="n/a", latency=None, vars=["ET0 method"], auth="none", live="methodology_reference",
                   adapter="earthsync.et0", numerical=False, lic=_lic("FAO publication", "https://www.fao.org/4/x0490e/x0490e00.htm", "Allen et al. (1998) FAO Irrigation and Drainage Paper 56", False, UNVERIFIED),
                   verify=dict(doc_checked=False, live_checked=False, note="Formulae implemented and tested against FAO-56 worked examples (see tests/test_et0.py)."),
                   notes=["EarthSync supplies ET0 as a forcing feature only; AquaSense owns Kc, paddy vs upland water balance."]),
    "FAO_AQUACROP": dict(pri=("P2", "P2", "P2"), app=(M, M, M), kind="methodology", spatial="n/a", temporal="n/a", latency=None, vars=[], auth="none", live="methodology_reference", adapter=None, numerical=False,
                         lic=_lic("FAO software terms", "https://www.fao.org/aquacrop/en", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "BARC_KHAMARI": dict(pri=("P0", "N/A", "N/A"), app=(N, X, X), kind="dataset", spatial="Upazila / soil series", temporal="Static", latency=None, vars=["land suitability", "soil series"],
                         auth="manual_download", live="manifest_only", adapter=None, lic=_lic("Unknown - published sources only", "https://cropzoning.gov.bd/", None, False, "No presumed public API; use published or authorized exports."),
                         verify=dict(doc_checked=False, live_checked=False), notes=["Owned by Agent 05."]),
    "LOCAL_CROP_STUDY": dict(pri=("P0", "N/A", "N/A"), app=(N, X, X), kind="dataset", spatial="Pilot region", temporal="Study-dependent", latency=None, vars=[], auth="manual_download", live="manifest_only", adapter=None,
                             lic=_lic("Per-paper", None, None, False, "Each paper has its own terms."), verify=dict(doc_checked=False, live_checked=False), notes=["Owned by Agent 05. The CSV official_url points at GAEZ and is not a study link."]),
    "LOCAL_MARKETS": dict(pri=("P1", "N/A", "N/A"), app=(N, X, X), kind="dataset", spatial="Market", temporal="Dated price observations", latency=None, vars=["price"], auth="unknown", live="manifest_only", adapter=None,
                          lic=_lic("Unknown", "https://market.dam.gov.bd/", None, False, "Terms unknown; do not scrape."), verify=dict(doc_checked=False, live_checked=False), notes=["Owned by AgriEconomics agent."]),
    "FARMER_GROUND": dict(pri=("P0", "P0", "P0"), app=(U, U, U), kind="user_input", spatial="Specific farm", temporal="Event-dated", latency=None, vars=["irrigation", "soil test", "salinity", "cost", "crop timing"],
                          auth="manual_download", live="manifest_only", adapter=None, numerical=True, lic=_lic("Farmer-owned", None, None, True, "User data; consent required."), verify=dict(doc_checked=False, live_checked=False),
                          notes=["Owned by AquaSense/FieldTwin. EarthSync never mixes farmer-reported values into NASA series; data_type=farmer_reported."]),
    # ---- US-only
    "USDA_CDL": dict(pri=("N/A", "P1", "N/A"), app=(X, N, X), kind="dataset", spatial="30 m (2008-2023), 10 m (2024+ per catalogue)", temporal="Annual", latency="~months after season", vars=["crop type"],
                     auth="manual_download", live="manifest_only", adapter=None, lic=_lic("US Government work (public)", "https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php", "USDA NASS", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "PRISM": dict(pri=("N/A", "P1", "N/A"), app=(X, N, X), kind="dataset", spatial="4 km daily; 800 m normals", temporal="Daily/monthly/normals", latency="~1 day provisional", vars=["ppt", "tmin", "tmax", "tdmean"],
                  auth="manual_download", live="offline_extract_ingest", adapter="earthsync.adapters.reference_csv", lic=_lic("PRISM terms of use", "https://prism.oregonstate.edu/", "PRISM Climate Group, Oregon State University", False, "Confirm terms, esp. bulk redistribution."),
                  verify=dict(doc_checked=False, live_checked=False), notes=["Independent gauge-based gridded comparison for the US pilot only. Ingest via declared-column CSV."]),
    "USDA_SSURGO_STATSGO": dict(pri=("N/A", "P1", "N/A"), app=(X, N, X), kind="dataset", spatial="Mapped polygons", temporal="Static", latency=None, vars=["texture", "OM", "AWC", "drainage", "HSG"], auth="none", live="manifest_only", adapter=None,
                                lic=_lic("US Government work (public)", None, "USDA NRCS", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "USDA_WSS": dict(pri=("N/A", "P2", "N/A"), app=(X, N, X), kind="dataset", spatial="Mapped polygons", temporal="Static", latency=None, vars=["soil properties"], auth="none", live="manifest_only", adapter=None,
                     lic=_lic("US Government work (public)", None, "USDA NRCS", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "USDA_QUICKSTATS": dict(pri=("N/A", "P1", "N/A"), app=(X, N, X), kind="dataset", spatial="County/state", temporal="Annual", latency=None, vars=["yield", "area"], auth="api_key", live="manifest_only", adapter=None,
                            lic=_lic("USDA NASS terms", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "USDA_AMS": dict(pri=("N/A", "P2", "N/A"), app=(X, N, X), kind="dataset", spatial="Market", temporal="Daily/weekly", latency=None, vars=["price"], auth="registration", live="manifest_only", adapter=None,
                     lic=_lic("USDA AMS terms", None, None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "USDA_AGCOMMONS": dict(pri=("P3", "P2", "P3"), app=(L, N, L), kind="discovery_portal", spatial="Varies", temporal="Varies", latency=None, vars=[], auth="none", live="manifest_only", adapter=None, numerical=False,
                           lic=_lic("Per-dataset", "https://data.nal.usda.gov/", None, False, "Each record has its own license."), verify=dict(doc_checked=False, live_checked=False)),
    "USDA_NAIP": dict(pri=("N/A", "P3", "N/A"), app=(X, N, X), kind="dataset", spatial="0.6-1 m", temporal="~2-3 year cycle per state", latency=None, vars=["aerial imagery"], auth="none", live="manifest_only", adapter=None,
                      lic=_lic("US Government work (public)", None, "USDA FSA", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "USGS_NLCD": dict(pri=("N/A", "P3", "N/A"), app=(X, N, X), kind="dataset", spatial="30 m", temporal="Multi-year", latency=None, vars=["land cover"], auth="none", live="manifest_only", adapter=None,
                      lic=_lic("US Government work (public)", None, "USGS MRLC", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "COCORAHS": dict(pri=("N/A", "P3", "N/A"), app=(X, N, X), kind="dataset", spatial="Gauge points (North America)", temporal="Daily", latency="Days", vars=["precipitation"], auth="none", live="manifest_only", adapter=None,
                     lic=_lic("CoCoRaHS data policy", "https://www.cocorahs.org/", None, False, "Confirm attribution/use terms."), verify=dict(doc_checked=False, live_checked=False),
                     notes=["Ground-gauge reference for IMERG/POWER in the US case; ingest via declared-column CSV."]),
    "USGS_NWIS": dict(pri=("N/A", "P3", "N/A"), app=(X, N, X), kind="dataset", spatial="Station points", temporal="Instantaneous-annual", latency="Near real-time", vars=["groundwater level", "streamflow"], auth="none", live="manifest_only", adapter=None,
                      lic=_lic("US Government work (public)", None, "USGS", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    "OPENET": dict(pri=("N/A", "P2", "N/A"), app=(X, L, X), kind="dataset", spatial="30 m field-scale", temporal="Monthly/daily", latency="Days-weeks", vars=["ET"], auth="api_key", live="manifest_only", adapter=None,
                   lic=_lic("OpenET terms", "https://etdata.org/", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                   notes=["Coverage is the western US: Iowa is outside the covered area, so OpenET is NOT applicable to the Story County pilot. Confirm coverage map."]),
    "LANDFIRE": dict(pri=("N/A", "P3", "N/A"), app=(X, N, X), kind="dataset", spatial="30 m", temporal="Periodic", latency=None, vars=["vegetation", "fuel"], auth="none", live="manifest_only", adapter=None,
                     lic=_lic("US Government work (public)", None, "USFS/USGS", False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False)),
    # ---- research paths
    "NVIDIA_EARTH2": dict(pri=("P3", "P3", "P3"), app=(L, L, L), kind="model_checkpoint", spatial="Model-dependent", temporal="Model-dependent", latency=None, vars=[], auth="none", live="do_not_use_live", adapter=None, numerical=False,
                          lic=_lic("Apache-2.0 code; model weights vary", "https://github.com/NVIDIA/earth2studio", None, False, "Check each checkpoint's license."), verify=dict(doc_checked=False, live_checked=False),
                          notes=["Research path only. Not NASA observations; no dependency in this module."]),
    "IBM_PRITHVI": dict(pri=("P3", "P3", "P3"), app=(L, L, L), kind="model_checkpoint", spatial="30 m (HLS-based)", temporal="Model-dependent", latency=None, vars=[], auth="none", live="do_not_use_live", adapter=None, numerical=False,
                        lic=_lic("Check Hugging Face model card", "https://huggingface.co/ibm-nasa-geospatial", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                        notes=["Research path only. Not a crop classifier without task-specific fine-tuning and validation."]),
    "KAGGLE_EXTERNAL": dict(pri=("P3", "P3", "P3"), app=(L, L, L), kind="dataset", spatial="Varies", temporal="Varies", latency=None, vars=[], auth="registration", live="do_not_use_live", adapter=None,
                            lic=_lic("Per-dataset", "https://www.kaggle.com/datasets", None, False, "Provenance often weak."), verify=dict(doc_checked=False, live_checked=False)),
    # ---- access services / visual only (not in CSV)
    "NASA_GIOVANNI": dict(pri=("P2", "P2", "P2"), app=(N, N, N), kind="access_service", name="NASA Giovanni (time-series/maps portal)", origin="Organizer-mentioned access path", cov="Global",
                          spatial="Product-dependent", temporal="Product-dependent", latency=None, vars=[], auth="earthdata_login", live="manifest_only", adapter=None,
                          lic=_lic("Per product", "https://giovanni.gsfc.nasa.gov/giovanni/", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                          caveat="Interactive tool; exported time series are valid inputs only via the declared-metadata extract ingest.",
                          notes=["Use for a one-off IMERG/SMAP point time series export; record product, version, area-averaging and units."]),
    "NASA_APPEEARS": dict(pri=("P2", "P2", "P2"), app=(N, N, N), kind="access_service", name="NASA AppEEARS (point/area sampler)", origin="Access path", cov="Global",
                          spatial="Product-dependent", temporal="Product-dependent", latency=None, vars=[], auth="earthdata_login", live="manifest_only", adapter=None,
                          lic=_lic("Per product", "https://appeears.earthdatacloud.nasa.gov/", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                          caveat="Requires Earthdata login and asynchronous task polling; designed for the HLS/SMAP point-sampling route, not implemented here.",
                          notes=["Best candidate for authenticated HLS/SMAP point extraction without downloading rasters."]),
    "NASA_WORLDVIEW": dict(pri=("P3", "P3", "P3"), app=(N, N, N), kind="visual_only", name="NASA Worldview (imagery browser)", origin="Organizer-mentioned", cov="Global",
                           spatial="Display tiles", temporal="Daily imagery", latency="Hours", vars=[], auth="none", live="do_not_use_live", adapter=None, numerical=False,
                           lic=_lic("NASA open imagery", "https://worldview.earthdata.nasa.gov/", None, False, UNVERIFIED), verify=dict(doc_checked=False, live_checked=False),
                           caveat="Colour-mapped display imagery is NOT numerical rainfall/vegetation data. Never read values off Worldview pixels.",
                           notes=["Organizer note: IMERG layers can be downloaded as images - those are pictures, not measurements."]),
}
# fmt: on

APPLICABILITY_KEYS = ("BD", "US", "GLOBAL")


def _csv_rows() -> dict[str, dict]:
    with open(DATA_DIR / "SOURCES_RELEVANT.csv", encoding="utf-8", newline="") as fh:
        return {r["source_id"]: r for r in csv.DictReader(fh)}


def build_manifest() -> list[SourceManifestEntry]:
    rows = _csv_rows()
    entries: list[SourceManifestEntry] = []
    ids = list(rows) + [k for k in OVERLAY if k not in rows]
    for sid in ids:
        ov = OVERLAY.get(sid)
        if ov is None:
            raise KeyError(f"No curated overlay for source {sid}; add it to manifest.OVERLAY")
        row = rows.get(sid)
        bd, us, gl = ov["pri"]
        a_bd, a_us, a_gl = ov["app"]
        verification = dict(ov.get("verify", {}))
        verification.setdefault("built_from", "SOURCES_RELEVANT.csv + organizer list + curated overlay" if row else "curated overlay (not in supplied CSV)")
        entries.append(SourceManifestEntry(
            source_id=sid,
            name=ov.get("name") or (row["source"] if row else sid),
            kind=ov["kind"],
            origin_group=(row["origin_group"] if row else ov.get("origin", "Added")),
            organizer_listed=sid in ORGANIZER_NAME,
            organizer_name=ORGANIZER_NAME.get(sid),
            priority_csv=(row["priority"] if row else "added"),
            priority_bd=bd, priority_us=us, priority_global=gl,
            applicability={"BD": a_bd, "US": a_us, "GLOBAL": a_gl},
            coverage=(row["coverage"] if row else ov.get("cov", "")),
            modules=[m for m in (row["modules"].split(";") if row else []) if m],
            decision_role=(row["decision_role"] if row else ov.get("caveat", "Access path / supporting reference")),
            native_spatial=ov["spatial"], native_temporal=ov["temporal"], latency=ov.get("latency"),
            variables=ov.get("vars", []), access_method=(row["access_method"] if row else ov.get("access", "See official URL")),
            auth_required=ov["auth"], live_decision=ov["live"], adapter_module=ov.get("adapter"),
            numerical_data=ov.get("numerical", True),
            critical_caveat=(row["critical_caveat"] if row else ov.get("caveat", "")),
            license=LicenseInfo(**ov["lic"]),
            official_url=(row["official_url"] if row else ov["lic"].get("url") or ""),
            verification=verification, notes=ov.get("notes", []),
        ))
    return entries


def write_manifest(path: Path = MANIFEST_JSON) -> Path:
    entries = build_manifest()
    path.write_text(json.dumps({"schema_version": "1.0.0", "generated_from": "earthsync.manifest.build_manifest()",
                                "count": len(entries), "sources": [e.model_dump(mode="json") for e in entries]}, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


_cache: Optional[dict[str, SourceManifestEntry]] = None


def load_manifest(refresh: bool = False) -> dict[str, SourceManifestEntry]:
    global _cache
    if _cache is None or refresh:
        _cache = {e.source_id: e for e in build_manifest()}
    return _cache


def get_source(source_id: str) -> SourceManifestEntry:
    m = load_manifest()
    if source_id not in m:
        raise KeyError(f"unknown source_id {source_id!r}; known: {sorted(m)}")
    return m[source_id]
