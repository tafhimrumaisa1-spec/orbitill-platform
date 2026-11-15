import test from 'node:test';
import assert from 'node:assert/strict';
import { BD_PACK, SAMPLE_FARM_BD } from '../modules/rootshift_runtime/src/index.js';
import { compareWithIntegratedSoilBrain } from '../services/rootshift_soilbrain.mjs';

test('shared platform composition uses evidence-gated SoilBrain', () => {
  const result = compareWithIntegratedSoilBrain({ farm:SAMPLE_FARM_BD, packs:{bd_rajshahi:BD_PACK} });
  assert.notEqual(result.decision.status, 'refused');
  assert.match(result.inputStatus.services.soilBrain, /^@orbitill\/soilbrain@/);
  assert.ok(result.candidates.some(candidate => candidate.softWarnings.some(warning => String(warning.code).startsWith('soilbrain.'))));
});
