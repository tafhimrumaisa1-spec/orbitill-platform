# Decision log

## 2026-11-15 — Global product hierarchy

ORBITILL is a global environmental and agricultural intelligence platform. Bangladesh and the United States are dedicated country experiences. Barind/Rajshahi is the first complete practical workflow, coastal Bangladesh is a priority pilot, and Iowa is the first US research pilot. Capability gates determine what analysis is available for every other location.

## 2026-11-15 — Integration architecture

Preserve each delivered module in its original folder. Add lossless adapters in `orbitill-platform` instead of editing or duplicating agent-owned algorithms during initial integration. Python owns scientific data and water/economics orchestration. RootShift remains a separately tested Node module until the final service boundary is proven.

## 2026-11-15 — Visual direction

Use image-led agricultural surfaces, warm limestone, deep forest, moss, clay, and restrained chartreuse. Avoid dense neon dashboards and large empty institutional panels. The interface should feel tactile and calm, with scientific details revealed progressively.

## 2026-11-15 — NASA offline bundles

Store integration-owned real NASA POWER bundles under `orbitill-platform/data/nasa-power` instead of mixing them with Agent 04's synthetic fixtures. The Agent 04 fetch script was repaired to support an output directory outside its own package. The bundle covers the same 1991–2025 period and variables for the Barind and Iowa pilots so the judge demo can run without live network access.

## 2026-11-15 — Real fixture discovery

Agent 04's loader originally searched only `real/` and `synthetic/` subdirectories, while its configurable fetch script writes directly to the selected output directory. The loader now supports both layouts. A platform integration test proves the Barind response is loaded as `fixture_real`, never synthetic, and retains its evidence identifier and daily time standard through the AquaSense boundary.

## 2026-11-15 — Conditional crop-season water pipeline

The first real vertical calculation uses verified Barind NASA POWER weather and AquaSense, but requires caller-supplied soil capacity, irrigation efficiency and crop-stage calendar values. Missing, physically invalid or cross-region inputs are refused rather than defaulted. Rainfall and irrigation-allowance controls create labelled hypothetical stress tests, recompute the water model and produce distinct run identifiers.

## 2026-11-15 — Agent 07 and 08 audit repairs

RootShift run identity now covers the actual climate payload and full region pack. It refuses mismatched region packs and invalid scenario multipliers, and unknown irrigation allowance produces unknown allocation, shortfall and economics rather than zero shortfall. FutureFields run identity now covers ET0, full economics, engine identity and provenance. It rejects non-finite or malformed weather and scenario/economics region mismatches. Stand-in service data remains clearly identified and is not promoted to evidence-backed output.

## 2026-11-15 — SoilBrain evidence gate

The incomplete Agent 05 paste was rebuilt as the vendored SoilBrain runtime, a dependency-free evidence-gated service. Canonical region IDs are `BD-RAJ-BARIND` and `US-IA-STORY`; RootShift's legacy IDs are translated only at the adapter boundary. Provisional evidence may inform a conditional result but cannot create a hard agronomic exclusion. A misattributed mungbean DOI and its claimed Bangladesh planting window were removed from executable rules. RootShift can now call the real SoilBrain adapter, while its own fixture calendar still controls scheduling until verified crop durations and windows are available.

## 2026-11-15 — Judgeable Barind vertical slice

Expose a water-focused three-pathway comparison rather than presenting RootShift's fixture economics as a result. The working planner evaluates T. Aman→Boro, T. Aman→Wheat and T. Aman→Mustard with the same declared soil, efficiency and allowance assumptions and verified NASA POWER weather. It labels incomplete crop calendars, refuses a universal winner and does not calculate yield or profit. This narrower slice is more defensible than a broader fixture-driven recommendation.

## 2026-11-15 — Shared editorial route

Mount the supplied Challenge, How It Works, Field Stories and Evidence web components under one `explore.html` hash router. The existing ORBITILL header remains the only global navigation, while Shadow DOM preserves the delivered component designs. App-specific status corrections are applied after mounting so editorial packages cannot overstate runtime integration. Product CTAs route to `planner.html`; research examples do not impersonate supported pilots.

