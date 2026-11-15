// Farmer-readable reasons. Codes + params are the contract; `text.en` is a convenience rendering (Bangla belongs to the i18n layer).
const T = {
  sowing_window_missed: (p) => `Cannot be sown in time: the field is free on ${p.earliestFree}, ${p.lateByDays} day(s) after the usual sowing window for ${p.crop} closed (${p.windowEnd}). Verify with your local agriculture office whether a shorter-duration variety or earlier harvest of the previous crop is possible.`,
  exceeds_horizon: (p) => `${p.crop} would be harvested on ${p.harvest}, ${p.overByDays} day(s) after the planning year ends (${p.horizonEnd}).`,
  crop_not_valid_in_region: (p) => `${p.crop} has no rules for this region (valid only in ${p.validIn.join(', ')}); region crop rules are never transplanted across countries.`,
  must_start_with_current_crop: (p) => `This plan must begin with the crop already in the field (${p.expected}).`,
  unknown_current_crop: () => 'The crop currently in the field is not in this region\'s crop list.',
  unknown_crop_in_pack: (p) => `${p.crop} is not in this region's crop list.`,
  severe_water_deficit: (p) => `${p.crop} would get about ${p.deficitPct}% less water than it needs. The linear yield-loss method is not reliable at that level, so treat its margin as a rough indication at best.`,
  late_in_window: (p) => `${p.crop} would be sown with only ${p.slackDays} day(s) left in the usual window; a small delay could make it infeasible.`,
  same_family_consecutive: (p) => `${p.crop} directly after ${p.previous} (same crop family): disease/pest carry-over risk — verify locally.`,
  current_crop_outside_window: (p) => `The current ${p.crop} was planted outside its usual window (already happened; shown for context).`,
  missing_current_crop_planting_date: (p) => `Planting date of the current ${p.crop} crop is missing, so no season dates can be computed.`,
  missing_environmental_series: (p) => `No ${p.needed} series is available (${p.intendedSource}); water results are withheld.`,
  missing_planning_horizon: () => 'The planning horizon is missing.',
  region_pack_missing: (p) => `No region pack for ${p.regionId}.`,
};
const MISS = {
  soil_texture: 'Soil texture is unknown — a soil test would settle whether drainage suits this crop.',
  soil_water_at_sowing: 'Soil water at sowing is unknown — irrigation need for dryland crops may be overstated.',
};
export const renderReason = (r) => ({ ...r, text: { en: (T[r.code] ?? (() => r.code))(r.params ?? {}) } });

export function buildReasons(r, { byId, pack, farm }) {
  const out = [];
  for (const h of r.hardViolations) out.push({ severity: 'blocking', ...renderReason(h) });
  for (const s of r.softWarnings) out.push({ severity: 'caution', ...renderReason(s) });
  for (const m of r.missing) out.push({ severity: 'verify', code: `missing_${m}`, params: {}, text: { en: MISS[m] ?? `Missing input: ${m}` } });
  if (r.water?.status === 'constrained') {
    const unc = r.economics?.marginUnconstrainedPerHa, lim = r.economics?.marginWaterLimitedPerHa;
    out.push({ severity: 'caution', code: 'water_constrained', params: { needMm: r.water.irrigationNeedMm, allowanceMm: r.water.allowanceMm, shortfallMm: r.water.shortfallMm, marginUnconstrained: unc, marginLimited: lim },
      text: { en: `Needs about ${Math.round(r.water.irrigationNeedMm)} mm of irrigation but only ${Math.round(r.water.allowanceMm)} mm is available. With full water the margin would be about ${unc?.toLocaleString('en-US')}, but with the water shortfall it falls to about ${lim?.toLocaleString('en-US')} (assumed prices and yield response).` } });
  }
  if (r.water?.status === 'allowance_unknown') out.push({ severity: 'verify', code: 'allowance_unknown', params: {}, text: { en: 'Available irrigation water is unknown, so the water limit could not be checked.' } });
  if (r.frontier && !r.frontier.onFrontier) {
    const d = byId[r.frontier.dominatedBy[0]];
    out.push({ severity: 'info', code: 'dominated', params: { by: d.id }, text: { en: `Another option (${d.id}) is at least as good on every compared measure and better on at least one.` } });
  }
  return out;
}

export function buildEvidenceTrace(result) {
  const lines = [];
  lines.push(`Model ${result.modelVersion}, input hash ${result.inputHash}.`);
  lines.push(`Decision status: ${result.decision.status}${result.decision.conditionalOn?.length ? ` (conditional on: ${result.decision.conditionalOn.join(', ')})` : ''}.`);
  lines.push(`Climate input: ${result.inputStatus?.climate?.provider} — ${result.inputStatus?.climate?.observationType ?? result.inputStatus?.climate?.status} (intended source: ${result.inputStatus?.climate?.intendedSource ?? 'n/a'}).`);
  for (const c of result.candidates) {
    lines.push(`\n[${c.id}] status=${c.status}${c.isBaseline ? ' (baseline)' : ''}`);
    for (const t of c.timeline) lines.push(`  ${t.cropId}: ${t.sow} -> ${t.harvest} (${t.dateType})`);
    if (c.objectives) lines.push(`  objectives: irrigation=${c.objectives.irrigationNeedMm ?? 'n/a'} mm, margin=${c.objectives.marginWaterLimitedPerHa} /ha, worst-case=${c.objectives.worstCaseMarginPerHa ?? 'fails in ' + c.robustness?.failedIn}, soil-qual=${c.objectives.soilQualitativeScore}`);
    for (const r of c.reasons) lines.push(`  - [${r.severity}] ${r.text.en}`);
    lines.push(`  evidence: ${c.lineage.map((l) => `${l.id}${l.verification === 'unverified_offline' ? '*' : ''}`).join(', ')}   (*unverified placeholder)`);
  }
  return lines.join('\n');
}
