import { evaluateCropFeasibility, MODEL_VERSION } from './evaluate.js';
import { getCropProfile } from './profiles.js';

const regionAliases = Object.freeze({ 'BD-RAJ':'BD-RAJ-BARIND', 'US-IA':'US-IA-STORY' });
const cropAliases = Object.freeze({ 'cereal-rye':'rye_cover', 'boro-rice':'boro' });
const iso = value => value instanceof Date ? value.toISOString().slice(0,10) : String(value).slice(0,10);

function rootShiftProfile(profile) {
  if (!profile) return undefined;
  return {
    id:profile.cropId, name:{en:profile.commonName}, family:profile.cropFamily,
    window:profile.plantingWindow?.earliest && profile.plantingWindow?.latest ? {start:profile.plantingWindow.earliest,end:profile.plantingWindow.latest} : undefined,
    durationDays:profile.durationDays, kc:undefined, ky:undefined, rice:Boolean(profile.rice), legume:Boolean(profile.legume), isCover:Boolean(profile.isCover),
    needsTexture:Boolean(profile.soilConstraints?.suitableTextures), evidence:profile.evidence.map(item => item.sourceId), verification:profile.evidence.every(item => item.status === 'verified') ? 'verified' : 'conditional'
  };
}

export function createRootShiftSoilBrainService() {
  return {
    provider:`@orbitill/soilbrain@${MODEL_VERSION}`,
    getCropProfile({region, cropId}) {
      const regionId = regionAliases[region?.id] ?? region?.id;
      return rootShiftProfile(getCropProfile(regionId, cropAliases[cropId] ?? cropId));
    },
    evaluateCropFeasibility({crop, sow, farm, region, previousCropId}) {
      const regionId = regionAliases[region?.id] ?? region?.id;
      const cropId = cropAliases[crop?.id] ?? crop?.id;
      const result = evaluateCropFeasibility({
        regionId, cropId, proposedSowingDate:iso(sow), previousCropId:cropAliases[previousCropId] ?? previousCropId,
        soil:{ textureClass: farm?.soil?.texture ? {value:farm.soil.texture, source: farm.soil.source === 'lab-test' ? 'lab_test' : 'farmer_report'} : undefined },
        constraints:{ waterAvailability: farm?.irrigationAvailableMm === undefined ? 'unknown' : farm.irrigationAvailableMm > 0 ? 'sufficient' : 'none' }
      });
      const item = rule => ({ code:`soilbrain.${rule.ruleId}`, params:{message:rule.message, evidence:rule.evidence.map(e => e.sourceId)}, text:rule.message });
      return {
        status:result.outcome === 'infeasible' || result.outcome === 'unsupported' ? 'violation' : result.outcome === 'feasible' ? 'ok' : 'conditional',
        hard:result.ruleResults.filter(rule => ['infeasible','unsupported'].includes(rule.outcome)).map(item),
        soft:result.ruleResults.filter(rule => ['conditional','insufficient_evidence'].includes(rule.outcome)).map(item),
        missing:result.missingMeasurements, modelRunId:result.modelRunId, evidence:result.evidence
      };
    }
  };
}
