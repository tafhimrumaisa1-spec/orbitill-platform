// compareRotations: farm + pack + scenario -> comparable RotationResult[] + Resilience Frontier.
import { createHash } from 'node:crypto';
import { isoDate, parseDate } from './calendar.js';
import { scheduleSequence, generateRotationCandidates, candidateId, MODEL_VERSION } from './schedule.js';
import { paretoFront, dominates, dominanceProof } from './pareto.js';
import { defaultServices } from './adapters/fixtures.js';
import { EVIDENCE } from './fixtures/evidence.js';
import { buildReasons, buildEvidenceTrace } from './explain.js';

/** Objectives. Each keeps its own unit; there is NO combined score. */
export const OBJECTIVES = {
  irrigationNeedMm: { direction: 'min', unit: 'mm per year over the field', label: 'Irrigation water needed', dataType: 'model estimate' },
  marginWaterLimitedPerHa: { direction: 'max', unit: 'currency per ha per year', label: 'Indicative gross margin (water-limited)', dataType: 'model estimate on assumed prices/yields' },
  worstCaseMarginPerHa: { direction: 'max', unit: 'currency per ha per year', label: 'Worst-case margin across defined stress scenarios', dataType: 'hypothetical scenario' },
  soilQualitativeScore: { direction: 'max', unit: 'count of legume/cover-crop seasons (ordinal, not measured)', label: 'Soil-protection indicator (qualitative)', dataType: 'published reference (direction only)' },
};
export const DEFAULT_ROBUSTNESS_SCENARIOS = [
  { id: 'dry_season', label: 'Drier season: rainfall x0.8 and pumping allowance x0.75 (hypothetical stress test, not a forecast)', rainfallMultiplier: 0.8, irrigationAllowanceMultiplier: 0.75 },
  { id: 'price_down', label: 'Crop prices x0.85 (hypothetical stress test)', priceMultiplier: 0.85 },
];

const stable = (o) => JSON.stringify(o, (k, v) => (v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v));
const sha = (o) => createHash('sha256').update(stable(o)).digest('hex').slice(0, 16);
const round = (x, n = 0) => (x === null || x === undefined ? null : +x.toFixed(n));

function evaluateCandidate(cand, ctx, scenario) {
  const { farm, pack, services, packs, climate } = ctx;
  const region = pack.region;
  const delay = scenario.amanTransplantDelayDays ?? 0;
  const { slots, structural } = scheduleSequence(cand.cropIds, farm, pack, { delayDays: delay });
  const hard = structural.map((st) => {
    if (st.code !== 'unknown_crop_in_pack') return st;
    const elsewhere = Object.values(packs).filter((p) => p !== pack && p.crops[st.params.crop]).map((p) => p.region.id);
    return elsewhere.length ? { code: 'crop_not_valid_in_region', params: { crop: st.params.crop, region: region.id, validIn: elsewhere } } : st;
  });
  const soft = [], missing = [];
  const timeline = [];
  let failedAt = -1;
  for (const [i, s] of slots.entries()) {
    if (failedAt >= 0) break; // later seasons depend on an invalid date; reporting them would be noise
    const prevId = i === 0 ? farm.previousCrop ?? null : slots[i - 1].crop.id;
    const r = services.soilBrain.evaluateCropFeasibility({ crop: s.crop, sow: s.sow, resolution: s.resolution, harvest: s.harvest, farm, region, previousCropId: prevId, packs });
    hard.push(...r.hard); soft.push(...r.soft); missing.push(...r.missing);
    if (s.fixed && s.resolution.outsideWindow) soft.push({ code: 'current_crop_outside_window', params: { crop: s.crop.id } });
    timeline.push({ cropId: s.crop.id, name: s.crop.name, sow: isoDate(s.sow), harvest: isoDate(s.harvest), windowEnd: s.resolution.window ? isoDate(s.resolution.window.end) : null, slackDays: s.resolution.slackDays ?? null, waitedDays: s.resolution.waitedDays ?? 0, fixed: s.fixed, dateType: s.fixed ? 'farmer-reported' : 'model estimate', infeasibleHere: r.hard.length > 0 });
    if (r.hard.length) failedAt = i;
  }
  if (hard.some((h) => h.code === 'sowing_window_missed')) for (let i = hard.length - 1; i >= 0; i--) if (hard[i].code === 'exceeds_horizon') hard.splice(i, 1);

  const feasible = hard.length === 0;
  let water = null, econ = null;
  const waterSupported = region.waterModel === 'supported';
  if (feasible || true) {
    // water & money are still computed for infeasible plans when dates exist, but never enter the frontier.
    const allowance = farm.irrigationAvailableMm === undefined ? null : farm.irrigationAvailableMm === null ? null : farm.irrigationAvailableMm * (scenario.irrigationAllowanceMultiplier ?? 1);
    if (waterSupported && climate && slots.length) {
      water = services.aquaSense.evaluateWaterBalance({ slots, climate, scenario, irrigationAvailableMm: allowance, soilWaterAtSowingMm: farm.soilWaterAtSowingMm ?? null });
      if (farm.soilWaterAtSowingMm == null && slots.some((s) => !s.crop.rice)) missing.push('soil_water_at_sowing');
    }
    for (const w of water?.perSlot ?? []) if (w.relativeDeficit > 0.5) soft.push({ code: 'severe_water_deficit', params: { crop: w.cropId, deficitPct: Math.round(w.relativeDeficit * 100) } });
    if (slots.length) econ = services.agriEconomics.calculateEconomics({ slots, water: waterSupported ? water : null, pack, scenario });
  }
  const legumeCount = slots.filter((s) => s.crop.legume || s.crop.isCover).length;
  let status = hard.length ? 'infeasible' : water?.status === 'constrained' ? 'water_constrained' : (missing.length || water?.status === 'allowance_unknown') ? 'conditional' : 'feasible';
  return { cand, slots, timeline, hard, soft, missing: [...new Set(missing)], water, econ, status, legumeCount, delay };
}

function robustness(cand, ctx, selected, scenarios) {
  const out = {};
  let worst = null, failed = null;
  for (const sc of scenarios) {
    const merged = { ...selected, ...sc, rainfallMultiplier: (selected.rainfallMultiplier ?? 1) * (sc.rainfallMultiplier ?? 1), irrigationAllowanceMultiplier: (selected.irrigationAllowanceMultiplier ?? 1) * (sc.irrigationAllowanceMultiplier ?? 1), priceMultiplier: (selected.priceMultiplier ?? 1) * (sc.priceMultiplier ?? 1) };
    const e = evaluateCandidate(cand, ctx, merged);
    const m = e.status === 'infeasible' ? null : e.econ?.totalMarginWaterLimitedPerHa ?? null;
    out[sc.id] = { label: sc.label, status: e.status, marginPerHa: m, irrigationNeedMm: e.water?.totalNeedMm ?? null, shortfallMm: e.water?.shortfallMm ?? null };
    if (m === null) failed = failed ?? sc.id; else worst = worst === null ? m : Math.min(worst, m);
  }
  return { byScenario: out, worstCaseMarginPerHa: failed ? null : worst, failedIn: failed };
}

/**
 * @param {object} input {farm, packs, regionPackId?, scenario?, robustnessScenarios?, objectives?, services?, simulate?}
 */
export function compareRotations(input) {
  const { farm, packs } = input;
  const services = { ...defaultServices, ...(input.services ?? {}) };
  const pack = packs[input.regionPackId ?? Object.values(packs).find((p) => p.region.id === farm.regionId)?.region.pack];
  if (!pack) return refuse(input, 'unknown_region', [{ code: 'region_pack_missing', params: { regionId: farm.regionId } }]);
  const scenario = input.scenario ?? { id: 'baseline', kind: 'baseline' };
  const robScenarios = input.robustnessScenarios ?? DEFAULT_ROBUSTNESS_SCENARIOS;
  const waterSupported = pack.region.waterModel === 'supported';
  const objectiveKeys = input.objectives ?? (waterSupported ? ['irrigationNeedMm', 'marginWaterLimitedPerHa', 'worstCaseMarginPerHa'] : ['marginWaterLimitedPerHa', 'worstCaseMarginPerHa', 'soilQualitativeScore']);
  const spec = objectiveKeys.map((k) => ({ key: k, direction: OBJECTIVES[k].direction }));

  // ---- essential-input gates: refuse rather than guess ----
  const gate = [];
  if (pack.region.id !== farm.regionId) gate.push({ code: 'region_pack_mismatch', params: { farmRegionId: farm.regionId, selectedRegionId: pack.region.id } });
  if (farm.currentCrop && !farm.currentCrop.plantedOn) gate.push({ code: 'missing_current_crop_planting_date', params: { crop: farm.currentCrop.cropId } });
  if (!farm.horizon?.start || !farm.horizon?.end) gate.push({ code: 'missing_planning_horizon', params: {} });
  for (const [name, value] of Object.entries({ rainfallMultiplier: scenario.rainfallMultiplier, irrigationAllowanceMultiplier: scenario.irrigationAllowanceMultiplier, priceMultiplier: scenario.priceMultiplier })) {
    if (value !== undefined && (!Number.isFinite(value) || value < 0)) gate.push({ code: 'invalid_scenario_multiplier', params: { name, value } });
  }
  const climate = waterSupported ? services.earthSync.getEnvironmentalSeries({ region: pack.region, packs, simulateMissing: input.simulate?.missingClimate }) : null;
  if (waterSupported && !climate) gate.push({ code: 'missing_environmental_series', params: { needed: 'rainfall + reference evapotranspiration', intendedSource: 'NASA POWER via EarthSync' } });
  if (gate.length) return refuse(input, 'refused', gate, pack);

  const ctx = { farm, pack, packs, services, climate };
  const candidates = generateRotationCandidates(farm, pack);
  const evals = candidates.map((c) => ({ c, e: evaluateCandidate(c, ctx, scenario) }));

  const results = evals.map(({ c, e }) => {
    const rob = e.status === 'infeasible' ? null : robustness(c, ctx, scenario, robScenarios);
    const econ = e.econ;
    const objectives = e.status === 'infeasible' ? null : {
      irrigationNeedMm: waterSupported ? round(e.water?.totalNeedMm, 0) : null,
      marginWaterLimitedPerHa: econ?.totalMarginWaterLimitedPerHa ?? null,
      worstCaseMarginPerHa: rob?.worstCaseMarginPerHa ?? null,
      soilQualitativeScore: e.legumeCount,
    };
    const meta = {
      irrigationNeedMm: waterSupported ? { uncertainty: e.missing.includes('soil_water_at_sowing') ? 'modelled; soil water at sowing unknown (need may be overstated for upland crops)' : 'modelled', ...OBJECTIVES.irrigationNeedMm } : { uncertainty: 'not modelled for this region pack', ...OBJECTIVES.irrigationNeedMm },
      marginWaterLimitedPerHa: { uncertainty: 'assumed yields, prices and costs (placeholder economics)', ...OBJECTIVES.marginWaterLimitedPerHa },
      worstCaseMarginPerHa: { uncertainty: 'only as good as the stress-scenario definition', basis: robScenarios.map((s) => s.id), ...OBJECTIVES.worstCaseMarginPerHa },
      soilQualitativeScore: { uncertainty: 'qualitative; no measured soil data used', ...OBJECTIVES.soilQualitativeScore },
    };
    return {
      id: c.id, label: c.label, kind: c.kind, isBaseline: c.isBaseline, cropIds: c.cropIds, status: e.status,
      timeline: e.timeline, hardViolations: e.hard, softWarnings: e.soft, missing: e.missing,
      water: e.status === 'infeasible' || !e.water ? null : { status: e.water.status, irrigationNeedMm: e.water.totalNeedMm, allowanceMm: e.water.allowanceMm, shortfallMm: e.water.shortfallMm, perCrop: e.water.perSlot, method: e.water.method },
      economics: e.status === 'infeasible' || !econ ? null : { currency: econ.currency, status: econ.status, marginWaterLimitedPerHa: econ.totalMarginWaterLimitedPerHa, marginUnconstrainedPerHa: econ.totalMarginUnconstrainedPerHa, perCrop: econ.perSlot, method: econ.method },
      objectives, objectiveMeta: meta, robustness: rob, frontier: null, reasons: [], lineage: null,
    };
  });

  // ---- Resilience Frontier over non-infeasible candidates ----
  const eligible = results.filter((r) => r.status !== 'infeasible' && r.objectives);
  const { frontier, dominated } = paretoFront(eligible, spec);
  const byId = Object.fromEntries(results.map((r) => [r.id, r]));
  for (const r of eligible) {
    const d = dominated.find((x) => x.id === r.id);
    r.frontier = { onFrontier: !d, dominatedBy: d?.dominatedBy ?? [] };
  }
  const dominanceExamples = dominated.slice(0, 3).map((d) => ({ dominated: d.id, dominator: d.dominatedBy[0], proof: dominanceProof(byId[d.dominatedBy[0]], byId[d.id], spec) }));

  // highlights (single-objective views; never a blended rank)
  const pickBy = (key, dir) => { const pool = eligible.filter((r) => r.objectives[key] !== null && r.objectives[key] !== undefined); if (!pool.length) return null; return pool.reduce((a, b) => (dir === 'max' ? (b.objectives[key] > a.objectives[key] ? b : a) : (b.objectives[key] < a.objectives[key] ? b : a))).id; };
  const highlights = { lowestWater: waterSupported ? pickBy('irrigationNeedMm', 'min') : null, highestMargin: pickBy('marginWaterLimitedPerHa', 'max'), mostRobust: pickBy('worstCaseMarginPerHa', 'max'), mostSoilProtective: pickBy('soilQualitativeScore', 'max') };
  const highestUnconstrained = eligible.filter((r) => r.economics?.marginUnconstrainedPerHa != null).sort((a, b) => b.economics.marginUnconstrainedPerHa - a.economics.marginUnconstrainedPerHa)[0];

  // shortlist: baseline + 2 alternatives (frontier members that differ most on water, then income)
  const hp = highestUnconstrained;
  const highProfitConstraint = hp ? { id: hp.id, status: hp.status, marginUnconstrainedPerHa: hp.economics.marginUnconstrainedPerHa, marginWaterLimitedPerHa: hp.economics.marginWaterLimitedPerHa, waterConstrained: hp.status === 'water_constrained' } : null;
  const alts = eligible.filter((r) => !r.isBaseline && r.kind !== 'reference_fallow');
  const frontAlts = alts.filter((r) => r.frontier.onFrontier);
  const pool = [...frontAlts, ...alts.filter((r) => !r.frontier.onFrontier)];
  const shortlist = [];
  const first = waterSupported ? [...pool].sort((a, b) => (a.objectives.irrigationNeedMm ?? Infinity) - (b.objectives.irrigationNeedMm ?? Infinity))[0] : [...pool].sort((a, b) => (b.objectives.marginWaterLimitedPerHa ?? -Infinity) - (a.objectives.marginWaterLimitedPerHa ?? -Infinity))[0];
  if (first) shortlist.push(first.id);
  const second = [...pool].filter((r) => r.id !== first?.id).sort((a, b) => (b.objectives.marginWaterLimitedPerHa ?? -Infinity) - (a.objectives.marginWaterLimitedPerHa ?? -Infinity))[0];
  if (second) shortlist.push(second.id);
  const baseline = results.find((r) => r.isBaseline);
  const display = [baseline?.id, ...shortlist].filter(Boolean);

  // lenses (ordered lists per farmer priority — the farmer chooses the lens, not us)
  const order = (key, dir) => eligible.filter((r) => r.frontier.onFrontier && r.objectives[key] != null).sort((a, b) => (dir === 'max' ? b.objectives[key] - a.objectives[key] : a.objectives[key] - b.objectives[key])).map((r) => r.id);
  const lenses = { water: waterSupported ? order('irrigationNeedMm', 'min') : [], income: order('marginWaterLimitedPerHa', 'max'), risk: order('worstCaseMarginPerHa', 'max'), soil: order('soilQualitativeScore', 'max') };

  const globalMissing = [...new Set(results.flatMap((r) => r.missing))];
  const status = farm.irrigationAvailableMm == null && waterSupported ? 'conditional' : globalMissing.length ? 'conditional' : 'ok';
  const inputHash = sha({ farm, scenario, robScenarios, pack, climate, objectiveKeys, providers: Object.fromEntries(Object.entries(services).map(([k, v]) => [k, v.provider])), v: MODEL_VERSION });

  for (const r of results) { r.reasons = buildReasons(r, { byId, pack, farm }); r.lineage = lineage(r, pack, climate, services); }

  const out = {
    schema: 'rootshift.compareRotations.v1', modelVersion: MODEL_VERSION, inputHash,
    decision: { status, recommendationAllowed: true, conditionalOn: globalMissing, note: 'RootShift presents trade-offs; it does not issue a single "best" crop or a confidence percentage.' },
    region: { id: pack.region.id, readiness: pack.region.readiness, waterModel: pack.region.waterModel }, horizon: farm.horizon,
    scenario, robustnessScenarios: robScenarios,
    frontierSpec: spec.map((s) => ({ ...s, ...OBJECTIVES[s.key] })), frontier, dominated, dominanceExamples,
    highlights: { ...highlights, highestUnconstrainedMargin: highestUnconstrained?.id ?? null }, highProfitConstraint,
    display, lenses, candidates: results,
    inputStatus: { climate: climate ? { provider: services.earthSync.provider, observationType: climate.observationType, intendedSource: climate.intendedSource } : { provider: waterSupported ? services.earthSync.provider : 'n/a', status: waterSupported ? 'missing' : 'not_used' }, services: Object.fromEntries(Object.entries(services).map(([k, v]) => [k, v.provider])) },
    evidenceTrace: null,
    limitations: LIMITATIONS,
  };
  out.evidenceTrace = buildEvidenceTrace(out);
  return out;
}

function lineage(r, pack, climate, services) {
  const ids = new Set(['ev:farmer-report']);
  for (const id of r.cropIds) (pack.crops[id]?.evidence ?? []).forEach((e) => ids.add(e));
  if (climate?.evidenceId) ids.add(climate.evidenceId);
  if (climate) ids.add('ev:nasa-power');
  ids.add('ev:scs-peff'); (pack.economics.evidence ?? []).forEach((e) => ids.add(e));
  return [...ids].map((id) => EVIDENCE[id]).filter(Boolean).map((e) => ({ id: e.id, provider: e.provider, title: e.title, url: e.url, role: e.role, dataType: e.dataType, verification: e.verification, note: e.note }));
}

function refuse(input, status, reasons, pack) {
  const farm = input.farm;
  return {
    schema: 'rootshift.compareRotations.v1', modelVersion: MODEL_VERSION, inputHash: sha({ farm, status, reasons }),
    decision: { status: 'refused', recommendationAllowed: false, reasons, note: 'An essential input is missing, so no confident comparison or frontier is produced. Nothing was guessed.' },
    region: pack ? { id: pack.region.id, readiness: pack.region.readiness } : null, horizon: farm?.horizon ?? null,
    scenario: input.scenario ?? null, frontier: [], dominated: [], candidates: [], display: [], lenses: {}, limitations: LIMITATIONS,
  };
}

export const LIMITATIONS = [
  'All crop windows, Kc/Ky values, climate normals and economics in this build are typed placeholders (fixtures); none are validated for any field.',
  'Rotation dates are planned at the earliest in-window sowing; real sowing depends on weather, labour and variety choice.',
  'Irrigation need uses a monthly water balance with season-average Kc; it is not a field measurement and does not use SMAP/HLS root-zone data.',
  'Margins use assumed yields, prices and costs; they are indicative, not forecasts.',
  'Stress scenarios are hypothetical, not forecasts. Worst-case is only worst among the listed scenarios.',
  'The FAO-33 linear yield response is only dependable for moderate water deficits; plans flagged severe_water_deficit (>50%) are outside that range and their margin is a rough indication only.',
  'The soil indicator is qualitative (legume/cover-crop seasons); no nutrient, salinity or disease modelling.',
];
