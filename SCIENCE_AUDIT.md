# Science audit

Updated 2026-11-15.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Real NASA series enters calculation | `data/nasa-power/POWER_BD_RAJSHAHI_BARIND_REAL.json.gz` → EarthSync → AquaSense | Pass |
| Units and dates preserved | EarthSync normalized observations and API evidence record | Pass |
| Baseline plus two alternatives | T. Aman→Boro, T. Aman→Wheat, T. Aman→Mustard | Pass, conditional |
| Scenario recomputes | Rainfall multiplier and irrigation allowance change model inputs and run IDs | Pass |
| Same assumptions across pathways | Shared soil, efficiency and selected allowance | Pass |
| Crop calendars locally verified | Wheat is an analogue; Boro and mustard incomplete | Not passed; visible limitation |
| Field soil measurement | Demonstration values only | Not passed; visible limitation |
| Economics | No source-compatible integrated Barind economics | Unavailable |
| Coastal salinity | No dated local bundle integrated | Unavailable |
| Evidence click-through | Result drawer exposes run, source ID, dates, assumptions and limits | Pass |

## Audit judgment

The Barind experience is scientifically defensible as a **conditional research demonstration of water implications**, not as a farm recommendation. The most important remaining scientific improvement is a locally verified crop-calendar and soil pack. Adding an unsupported profit score would reduce validity and is rejected for this release.
