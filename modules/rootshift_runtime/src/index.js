export { compareRotations, OBJECTIVES, DEFAULT_ROBUSTNESS_SCENARIOS, LIMITATIONS } from './compare.js';
export { runScenario } from './scenario.js';
export { generateRotationCandidates, scheduleSequence, enumerateSequences, MODEL_VERSION } from './schedule.js';
export { paretoFront, dominates, dominanceProof } from './pareto.js';
export { buildEvidenceTrace, renderReason } from './explain.js';
export { defaultServices } from './adapters/fixtures.js';
export { BD_PACK, SAMPLE_FARM_BD } from './fixtures/bd_rajshahi.js';
export { US_PACK, SAMPLE_FARM_US } from './fixtures/us_iowa.js';
export { EVIDENCE } from './fixtures/evidence.js';
