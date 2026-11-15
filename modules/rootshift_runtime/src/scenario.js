// FutureFields integration stub: apply scenario deltas, recompute with the real engine, and diff vs baseline.
import { compareRotations } from './compare.js';

/** delta: {rainfallMultiplier?, irrigationAllowanceMultiplier?, priceMultiplier?, amanTransplantDelayDays?} — hypothetical, not forecasts. */
export function runScenario(input, delta, label = 'Scenario') {
  const base = compareRotations({ ...input, scenario: { id: 'baseline', kind: 'baseline' } });
  const scenario = { id: 'user_scenario', kind: 'hypothetical scenario', label, ...delta };
  const run = compareRotations({ ...input, scenario });
  const diffs = run.candidates.map((c) => {
    const b = base.candidates.find((x) => x.id === c.id);
    return { id: c.id, statusBefore: b?.status, statusAfter: c.status,
      irrigationNeedMm: { before: b?.objectives?.irrigationNeedMm ?? null, after: c.objectives?.irrigationNeedMm ?? null },
      marginPerHa: { before: b?.objectives?.marginWaterLimitedPerHa ?? null, after: c.objectives?.marginWaterLimitedPerHa ?? null },
      onFrontier: { before: b?.frontier?.onFrontier ?? null, after: c.frontier?.onFrontier ?? null } };
  });
  return { kind: 'ModelRun', baselineHash: base.inputHash, scenarioHash: run.inputHash, scenario, diffs, base, run };
}
