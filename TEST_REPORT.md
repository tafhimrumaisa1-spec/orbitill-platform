# Test report

Run 2026-11-15 on the local integration workspace.

## Passing automated checks

| Suite | Result | What it covers |
| --- | --- | --- |
| Platform Python integration | 15 passed | Contracts, validation, real POWER fixture discovery, provenance transfer, missing-data refusal, crop-season water, three-pathway demo and scenario recomputation |
| Platform Node boundary and editorial routing | 4 passed | RootShift/SoilBrain composition, four top-bar destinations, eight-technology ecosystem and conservative status language |
| SoilBrain | 13 passed | Regional gating, provisional evidence, missing rules, input bounds and RootShift adapter |
| RootShift | 46 passed | Scheduling, three pathways, refusal logic, Pareto behavior, scenarios, determinism, lineage, water closure and schema |
| FutureFields | 19 passed | Scenario identity, validation, economics availability and malformed-input behavior |
| TerraLens | 175 passed | API envelopes, regional routing, Bangla search, boundary hashes, geometry/area validation, readiness caps, source licenses and refusal behavior |
| Web structural audit | 6 pages passed | Local files, fragments and duplicate HTML IDs, including the nested TerraLens entry page |

Total executed: **272 passing automated tests, 0 failures**.

JavaScript syntax checks passed for `planner.js`, `app.js` and `bangladesh.js`.

## Manual/API verification

- `GET /planner.html` returned HTTP 200 from the integrated server.
- `POST /api/demo/barind/compare` returned three conditional pathways.
- Changing rainfall to 75% and the seasonal allowance to 400 mm returned a new comparison run ID and three new pathway run IDs.
- Desktop 1440×1100 and mobile 390×844 screenshots were rendered with the actual API active.
- Challenge, How It Works and Evidence routes were rendered through the shared top-bar shell; supplied component styles remained Shadow-DOM isolated.
- TerraLens desktop and mobile routes loaded through the combined server; its processed data version was `3332eba9b9407b22` with 8 divisions, 64 districts, 544 ADM3 polygons, 99 Iowa counties and 242 country features.
- TerraLens search/profile/field APIs returned typed envelopes; Barind handed off to `/planner.html`, while coastal Bangladesh and Iowa remained gated because no compatible downstream decision model is integrated.
- Planner failure behavior was inspected in code: an unavailable API shows no substitute result numbers.
- Secret-pattern scan found no likely API key, password or private-key material in `orbitill-platform` text files.

## Not rerun in this environment

- EarthSync’s complete upstream suite (delivery reports 115 passed and 3 live tests skipped).
- AquaSense’s complete upstream suite (delivery reports 89 passed).
- Live NASA network test; the judge path intentionally uses the verified offline bundle.
- Hosted clean-browser and public-URL tests, because no deployment has been authorized.

## Release interpretation

The tested vertical slice is suitable for a conditional research demonstration. It is not a validated advisory system, and the unresolved calendar/soil/economics limitations in `SCIENTIFIC_LIMITATIONS.md` remain release-visible.
