# ORBITILL: RootShift — Exploring Agricultural Futures with NASA Earth Observations

ORBITILL is a NASA Space Apps Challenge 2026 project that explores how Earth observations, regional agronomy and farmer-defined constraints can support more transparent conversations about future cropping strategies. It combines a global capability explorer with distinct Bangladesh and United States research experiences, while refusing to present one regional model as universally valid.

The first working scientific demonstration focuses on the Barind/Rajshahi context in Bangladesh. It uses verified offline NASA POWER daily weather data to compare the water implications of an existing crop pathway with two alternatives. Changing the rainfall multiplier or seasonal irrigation allowance triggers a real recomputation and a new model-run identity. Every displayed result retains its evidence, assumptions and limitations.

ORBITILL is a **conditional research demonstration**, not a farm recommendation, yield forecast or validated advisory service. NASA POWER is gridded environmental context rather than an in-field sensor, and the current Barind run uses explicitly declared demonstration soil, irrigation-efficiency and incomplete crop-calendar inputs.

## What works in this release

- A responsive World experience with dedicated Bangladesh and United States editorial journeys.
- TerraLens global, Bangladesh and US exploration with offline administrative boundaries, place search, field-geometry checks, native-grid explanations and capability gates.
- Verified, non-synthetic offline NASA POWER bundles for the Barind and Story County, Iowa reference locations.
- A working Barind comparison of T. Aman → Boro, T. Aman → Wheat and T. Aman → Mustard pathways on a shared assumption basis.
- Genuine rainfall and irrigation-allowance recomputation through EarthSync and AquaSense, with deterministic run identities.
- Result-level evidence inspection showing source identifiers, observation dates, assumptions, warnings and scientific limitations.
- Evidence-gated SoilBrain and RootShift integration boundaries, plus accessible desktop and mobile navigation.

## Scientific readiness

| Capability | Current public-release status |
| --- | --- |
| NASA environmental series | **Working.** Real offline POWER data are verified for Barind and Iowa, with dates, units, grid support and provenance preserved. |
| TerraLens region explorer | **Working.** Global, Bangladesh and US geography is capability-gated; boundaries are cartographic and never described as cadastral or farm measurements. |
| Barind water comparison | **Working, conditional.** Three pathways use the same declared soil, efficiency and scenario assumptions. Results describe modeled water implications only. |
| Scenario testing | **Working.** Rainfall and irrigation changes alter model inputs, outputs and run identities; they are hypothetical stress tests, not forecasts. |
| Crop and soil feasibility | **Conditional/incomplete.** SoilBrain is integrated, but Barind wheat is provisional and several crop calendars and soil thresholds remain unavailable. |
| Iowa decision model | **Incomplete.** POWER context and evidence-gated rules exist, but USDA soil integration, validated economics and a complete Iowa decision run do not. |
| Economics, yield and profit | **Unavailable in the working Barind run.** No compatible local economics or yield model is presented. |
| Coastal Bangladesh recommendations | **Unavailable.** Exploration is supported, but crop conclusions remain blocked without dated local salinity, crop-calendar and compatible economic evidence. |
| Conversational FieldPilot | **Not included.** The deterministic EvidenceLayer works; a runnable conversational agent was not delivered for this release. |

The detailed scientific judgment is recorded in [SCIENCE_AUDIT.md](SCIENCE_AUDIT.md), [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) and [SCIENTIFIC_LIMITATIONS.md](SCIENTIFIC_LIMITATIONS.md).

## Project structure

- `apps/web` contains the shared responsive product shell and regional/editorial pages.
- `apps/web/planner.html` is the working Barind research demonstration.
- `apps/web/terralens/` contains the integrated TerraLens interface, vendored map renderer and processed browser boundary bundle.
- `services/science_api` contains evidence-preserving adapters, validation and the integrated JSON API.
- `services/science_api/water_pipeline.py` runs crop-season water simulations only when explicit soil, efficiency and calendar inputs are supplied.
- `services/rootshift_soilbrain.mjs` composes the vendored RootShift and evidence-gated SoilBrain runtimes.
- `modules` contains the audited runtime packages required by a standalone public clone.
- `data/nasa-power` contains the verified offline NASA POWER bundles for Barind and Iowa.
- `tests` and `tests_node` exercise scientific contracts and module integration boundaries.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer for the JavaScript integration tests
- Dependencies listed in `requirements.txt`

Install the Python dependencies in your preferred virtual environment:

```sh
python -m pip install -r requirements.txt
```

## Local preview

Run `./run_local.ps1` on Windows or `sh ./run_local.sh` on Linux/WSL, then open `http://127.0.0.1:8400/`. The integrated server is required for calculated planner results; the planner refuses to substitute static values when the API is unavailable.

Run the local integration API directly with:

```powershell
python -m services.science_api.server
```

It exposes `GET /api/health`, `GET /api/regions`, validated `POST /api/demo/barind/compare`, and namespaced TerraLens routes under `/api/terralens/*` on port 8400 while serving the frontend from the same origin.

Useful local routes:

- World: `http://127.0.0.1:8400/`
- Bangladesh: `http://127.0.0.1:8400/bangladesh.html`
- United States: `http://127.0.0.1:8400/usa.html`
- TerraLens: `http://127.0.0.1:8400/terralens/`
- Barind comparison: `http://127.0.0.1:8400/planner.html`

## Tests

From the repository root, run:

```sh
python -B scripts/run_python_tests.py
node --test "tests_node/*.test.mjs"
node scripts/audit_web.mjs
```

The vendored runtime packages are added automatically. The latest recorded audit is in [TEST_REPORT.md](TEST_REPORT.md).

## Data, evidence and licensing

NASA POWER observations, retrieval metadata and transformation boundaries are documented in [DATA_PROVENANCE.md](DATA_PROVENANCE.md). Scientific sources, boundary datasets, generated editorial illustrations, fonts and MapLibre licensing are registered in [SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md).

Project-authored code is released under the [Apache License 2.0](LICENSE). Bundled third-party assets retain their respective licenses and attribution. ORBITILL is an independent NASA Space Apps Challenge project and does not imply endorsement by NASA or any cited institution.

## Release and deployment

The repository includes a Vercel Python entry point and static-site configuration. See [DEPLOYMENT.md](DEPLOYMENT.md) for the GitHub/Vercel release procedure. Publication and final NASA submission remain participant-controlled actions.
