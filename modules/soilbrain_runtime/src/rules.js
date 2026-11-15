import { isValidMonthDay } from './validation.js';

function evidenceGatedOutcome(evidence, supportedOutcome) {
  if (evidence?.status === 'verified') return supportedOutcome;
  return 'conditional';
}

export function checkRegion(profile, input) {
  if (profile.regionId === input.regionId) return { ruleId:'region-match', outcome:'feasible', message:'Crop profile matches the selected regional pack.', evidence:[] };
  return { ruleId:'region-match', outcome:'infeasible', message:`${profile.cropId} is scoped to ${profile.regionId}, not ${input.regionId}.`, evidence:profile.evidence ?? [] };
}

export function checkPlantingWindow(profile, input) {
  const window = profile.plantingWindow;
  if (!window) return { ruleId:'planting-window', outcome:'insufficient_evidence', message:'No region-valid planting window is encoded for this crop.', evidence:[], missingMeasurements:['crop.plantingWindow'] };
  if ((window.earliest && !isValidMonthDay(window.earliest)) || (window.latest && !isValidMonthDay(window.latest))) {
    return { ruleId:'planting-window', outcome:'unsupported', message:'The crop profile contains an invalid planting-window boundary.', evidence:[window.evidence] };
  }
  const md = input.proposedSowingDate.slice(5);
  let inside = true;
  if (window.earliest && window.latest) {
    inside = window.earliest <= window.latest ? md >= window.earliest && md <= window.latest : md >= window.earliest || md <= window.latest;
  } else if (window.earliest) inside = md >= window.earliest;
  else if (window.latest) inside = md <= window.latest;
  const confidence = window.evidence.status;
  if (inside) {
    return { ruleId:'planting-window', outcome:evidenceGatedOutcome(window.evidence, 'feasible'), message:`Sowing date is within the ${window.earliest ?? 'open'}–${window.latest ?? 'open'} window (${confidence} evidence).`, evidence:[window.evidence] };
  }
  return { ruleId:'planting-window', outcome:evidenceGatedOutcome(window.evidence, 'infeasible'), message:`Sowing date is outside the ${window.earliest ?? 'open'}–${window.latest ?? 'open'} window (${confidence} evidence).`, evidence:[window.evidence] };
}

export function checkSoil(profile, soil = {}) {
  const constraints = profile.soilConstraints ?? {};
  const configured = Object.keys(constraints).length;
  if (!configured) return { ruleId:'soil-constraints', outcome:'insufficient_evidence', message:'No region-valid numerical soil thresholds are encoded; supplied soil values are preserved but not judged.', evidence:[], missingMeasurements:[] };
  const checks = [];
  if (constraints.phRange) {
    if (!soil.ph) checks.push({missing:'soil.ph'});
    else checks.push({pass:soil.ph.value >= constraints.phRange.min && soil.ph.value <= constraints.phRange.max, evidence:constraints.phRange.evidence});
  }
  const missing = checks.filter(x => x.missing).map(x => x.missing);
  if (missing.length) return { ruleId:'soil-constraints', outcome:'conditional', message:'Required soil measurements are missing.', evidence:[], missingMeasurements:missing };
  const failing = checks.find(x => x.pass === false);
  if (failing) return { ruleId:'soil-constraints', outcome:evidenceGatedOutcome(failing.evidence, 'infeasible'), message:'A supplied soil measurement is outside an encoded range.', evidence:[failing.evidence] };
  return { ruleId:'soil-constraints', outcome:checks.some(x => x.evidence?.status !== 'verified') ? 'conditional' : 'feasible', message:'Supplied soil measurements satisfy the encoded constraints.', evidence:checks.map(x => x.evidence).filter(Boolean) };
}

export function checkWater(profile, availability = 'unknown') {
  if (profile.waterRequirement === 'unknown') return { ruleId:'water-availability', outcome:'insufficient_evidence', message:'The crop water-dependence rule is not encoded for this regional profile.', evidence:[], missingMeasurements:['crop.waterRequirement'] };
  if (profile.waterRequirement === 'irrigation_required' && availability === 'none') return { ruleId:'water-availability', outcome:'infeasible', message:'This crop profile requires irrigation, but the farm reports none.', evidence:[] };
  if (availability === 'unknown') return { ruleId:'water-availability', outcome:'conditional', message:'Farm water availability is unknown.', evidence:[], missingMeasurements:['constraints.waterAvailability'] };
  if (profile.waterRequirement === 'irrigation_required' && availability === 'limited') return { ruleId:'water-availability', outcome:'conditional', message:'Irrigation is required and reported as limited; a water-balance calculation is needed.', evidence:[] };
  return { ruleId:'water-availability', outcome:'feasible', message:'The reported water category does not trigger this crop rule.', evidence:[] };
}

export function checkSequence(previousCropId, nextCropId, regionId) {
  if (!previousCropId) return { ruleId:'crop-sequence', outcome:'insufficient_evidence', message:'No previous crop was supplied.', evidence:[], missingMeasurements:['previousCropId'] };
  if (regionId === 'US-IA-STORY' && previousCropId === 'rye_cover' && nextCropId === 'soybean') {
    return { ruleId:'crop-sequence', outcome:'feasible', message:'Iowa NRCS identifies cereal rye as a suitable cover crop before soybean, with management caveats.', evidence:[] };
  }
  return { ruleId:'crop-sequence', outcome:'insufficient_evidence', message:'This crop succession is not encoded as a region-valid rule.', evidence:[] };
}
