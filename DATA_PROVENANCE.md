# Environmental data provenance

## Verified NASA POWER bundles

| Region profile | Requested point | Period | Variables | Fixture |
| --- | --- | --- | --- | --- |
| `BD-RAJ-BARIND` | 24.3745 N, 88.6042 E | 1991-01-01 through 2025-12-31 | T2M, T2M_MAX, T2M_MIN, T2MDEW, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M, PS | `data/nasa-power/POWER_BD_RAJSHAHI_BARIND_REAL.json.gz` |
| `US-IA-STORY` | 42.0308 N, 93.6319 W | 1991-01-01 through 2025-12-31 | T2M, T2M_MAX, T2M_MIN, T2MDEW, PRECTOTCORR, ALLSKY_SFC_SW_DWN, RH2M, WS2M, PS | `data/nasa-power/POWER_US_IOWA_STORY_REAL.json.gz` |

Retrieval and verification details are in `data/nasa-power/FETCH_REPORT.json`, including the original NASA API URLs and retrieval timestamp (`2026-11-15T10:16:32Z`). Each variable has 12,784 valid daily values. The fetcher's same-cell perturbation check reported identical grid-cell values for both pilots. That is expected for a gridded product and is evidence that these values must not be described as field-scale measurements.

## Scientific handling rules

- Raw responses stay compressed and unchanged; transformations occur after loading.
- EarthSync creates the evidence record and identifier. The integration adapter preserves that identifier through weather validation.
- Synthetic fixtures remain labelled and are rejected by the real-pilot pipeline.
- Exact weather rows, requested dates, coordinates, evidence identifiers and model versions enter the run hash.
- Daily time semantics currently remain `provider_default`. Comparisons with farmer-reported events must display this limitation until the day boundary is explicitly normalized and documented.
- NASA POWER supports climate and crop-water context. It cannot establish field salinity, root-zone soil water, soil texture, local prices or agronomic suitability by itself.

## Coverage still required

Coastal Bangladesh is a first-class priority but does not yet have a verified environmental bundle in this repository. The integration layer returns `unavailable` rather than borrowing Barind data. Responsible coastal analysis also requires dated local soil or irrigation-water salinity evidence and a coastal agronomic rule pack.
