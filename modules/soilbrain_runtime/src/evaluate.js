import { createHash } from 'node:crypto';
import { getCropProfile } from './profiles.js';
import { uniqueEvidence } from './evidence.js';
import { validateInput } from './validation.js';
import { checkPlantingWindow, checkRegion, checkSequence, checkSoil, checkWater } from './rules.js';

export const MODEL_VERSION = 'soilbrain-rules-0.2.0';
const rank = { unsupported:5, infeasible:4, conditional:3, insufficient_evidence:2, feasible:1 };

function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${stable(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}

function runId(input, profile) {
  return `sbr_${createHash('sha256').update(stable({input, profile, modelVersion:MODEL_VERSION})).digest('hex').slice(0, 20)}`;
}

function refusal(input, message, ruleId = 'input-validation') {
  const safeInput = input && typeof input === 'object' ? input : {};
  return { schemaVersion:'1.0.0', modelVersion:MODEL_VERSION, modelRunId:runId(safeInput, null), regionId:safeInput.regionId ?? 'unknown', cropId:safeInput.cropId ?? 'unknown', outcome:'unsupported', ruleResults:[{ruleId,outcome:'unsupported',message,evidence:[]}], missingMeasurements:[], unsupportedFields:[], evidence:[], limitations:['No recommendation was computed.'] };
}

export function evaluateCropFeasibility(input, suppliedProfile) {
  const errors = validateInput(input);
  if (errors.length) return refusal(input, errors.join('; '));
  const profile = suppliedProfile ?? getCropProfile(input.regionId, input.cropId);
  if (!profile) return refusal(input, `No crop profile exists for ${input.cropId} in ${input.regionId}.`, 'profile-lookup');
  if (input.cropId !== profile.cropId && !profile.aliases?.includes(input.cropId)) return refusal(input, 'Input cropId does not match the supplied crop profile.', 'profile-identity');
  const region = checkRegion(profile, input);
  const rules = [region];
  if (region.outcome !== 'infeasible') {
    rules.push(checkPlantingWindow(profile, input));
    rules.push(checkSoil(profile, input.soil));
    rules.push(checkWater(profile, input.constraints?.waterAvailability));
    if (input.previousCropId) rules.push(checkSequence(input.previousCropId, profile.cropId, input.regionId));
  }
  const outcome = [...rules].sort((a,b) => rank[b.outcome] - rank[a.outcome])[0].outcome;
  const evidence = uniqueEvidence([...profile.evidence, ...rules.flatMap(rule => rule.evidence ?? [])]);
  return {
    schemaVersion:'1.0.0', modelVersion:MODEL_VERSION, modelRunId:runId(input, profile), regionId:input.regionId, cropId:profile.cropId,
    outcome, ruleResults:rules, missingMeasurements:[...new Set(rules.flatMap(rule => rule.missingMeasurements ?? []))],
    unsupportedFields:[...profile.unsupportedFields], evidence,
    limitations:['Rule-based research-pilot result; not a yield forecast or field diagnosis.', 'Mapped or farmer-reported soil values do not become laboratory measurements.', ...profile.evidenceNotes]
  };
}
