# Sources and licenses

Updated 2026-11-15. This is a release register, not legal advice. Recheck every external asset before public publication.

| Item | Purpose | Origin | License / terms | Release note |
| --- | --- | --- | --- | --- |
| NASA POWER daily data | Barind and Iowa environmental series | https://power.larc.nasa.gov/ | NASA open-data terms; cite NASA POWER | Integrated with dates, units and grid support |
| NASA POWER methodology | Interpretation and limitations | https://power.larc.nasa.gov/docs/methodology/ | NASA public documentation | Directly linked in product |
| FAO Irrigation and Drainage Paper 56 | ET0, Kc, crop-water coefficients and reference stage analogues | https://www.fao.org/4/x0490e/x0490e00.htm | FAO publication; attribution required | Reference method, not local validation |
| Bangladesh Bank July 2026 report | Agricultural-employment context | https://www.bb.org.bd/pub/monthly/agri_nonfarm/publication%20july%202026.pdf | Public institutional report | Bangladesh page cites report and date |
| FAO/GIEWS Bangladesh brief, 4 Sep 2026 | Cereal imports and IPC context | https://cb.apps.fao.org/country/BGD/pdf/BGD.pdf | FAO public report; attribution required | Bangladesh page cites exact pages |
| World Bank release, 26 Jun 2026 | Fertilizer-import context | https://www.worldbank.org/en/news/press-release/2026/06/26/bangladesh-world-bank-provides-1-1-billion-emergency-support-to-safeguard-food-security-livelihoods | World Bank website terms | Bangladesh page links exact release |
| USDA NRCS Iowa cereal-rye references | SoilBrain Iowa research context | Recorded in `modules/soilbrain_runtime/src/evidence.js` | US Government/public source; verify individual page terms | Not transferred to Bangladesh |
| Iowa State CARD and Extension pages | USA editorial context | Exact links in `apps/web/usa.html` | Site terms; citation/link use only | No copied photography |
| World Bank / IWMI Barind research note | Challenge-page groundwater context | https://documents1.worldbank.org/curated/en/888071579802640956/pdf/Pro-Poor-Groundwater-Development-The-Case-of-the-Barind-Experiment-in-Bangladesh.pdf | Public institutional research; attribution required | No farm-level groundwater claim |
| IRRI Asian mega-delta webinar summary | Coastal waterlogging/salinity context | https://news.irri.org/2024/10/webinar-highlights-innovations-for.html | Public institutional page; citation/link use only | Editorial context, not ORBITILL output |
| Punjab groundwater research | Field Stories research example | https://www.sciencedirect.com/science/article/pii/S2352801X24000407 | Publisher terms; citation/link use only | Not an ORBITILL pilot |
| Kenya State of the Climate 2025 | Field Stories research example | https://meteo.go.ke/documents/3009/State_of_the_Climate_Report_2025.pdf | Public government report; attribution required | No inferred yield/forecast value |
| Embrapa/Cerrado maize and cover-crop research | Field Stories research example | https://rbms.sede.embrapa.br/ojs/article/view/1345 | Publisher terms; citation/link use only | Site-specific research, not an ORBITILL pilot |
| geoBoundaries Bangladesh ADM0/ADM1 | TerraLens national/division boundaries | geoBoundaries release pin `9469f09` | CC0 1.0 Universal | Integrated; cartographic boundaries only |
| BBS/OCHA Bangladesh ADM2/ADM3 via geoBoundaries | TerraLens district/upazila context | geoBoundaries release pin `9469f09`, 2020 files | CC BY 3.0 IGO; attribution preserved | Integrated; 64 districts and 544 polygons including metropolitan thanas |
| US Census MAF/TIGER via geoBoundaries | TerraLens state and Iowa county context | geoBoundaries release pin `9469f09`, 2018 files | Public Domain | Integrated; not parcel/cadastral data |
| Natural Earth 5.1.2 | TerraLens global country outlines | Natural Earth 50m/110m Admin-0 | Public Domain | Integrated for orientation; not legal boundaries |
| NASA GIBS / EOSDIS | Optional TerraLens raster display | https://gibs.earthdata.nasa.gov/ | NASA open-data terms; attribution required | Visualization context only; no raster value is treated as a field measurement |
| MapLibre GL JS | TerraLens map renderer | Bundled in `apps/web/terralens/vendor/maplibre` | BSD-3-Clause; included `LICENSE.txt` | Integrated |
| Manrope, Fraunces, Noto Sans Bengali | TerraLens typography | Bundled font files | SIL Open Font License; included OFL files | Integrated |
| ORBITILL editorial illustrations | Homepage and regional storytelling | Generated with OpenAI ImageGen on 2026-11-15 | Generated media; disclose AI use per event rules | Prompts recorded in `apps/web/assets/IMAGE_PROMPTS.md` |
| User-provided inspiration screenshots | Private visual direction only | User-supplied | Not cleared for publication | Not included as production assets |

## Code licensing

ORBITILL integration code is prepared under Apache License 2.0 in `LICENSE`, subject to the participant’s final review. Third-party components retain their original licenses.

## Before publication

1. Confirm any future photography has an explicit reusable license or is participant-owned.
2. Preserve NASA/FAO/World Bank/geoBoundaries attribution and avoid suggesting endorsement.
3. Run a final secret, EXIF, PII and dependency-license scan.
4. Confirm the participant has authority to release all agent-delivered module code under Apache-2.0; the original RootShift and SoilBrain delivery metadata identified those packages as `UNLICENSED`.
