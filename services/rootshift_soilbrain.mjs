import { compareRotations } from '../modules/rootshift_runtime/src/index.js';
import { createRootShiftSoilBrainService } from '../modules/soilbrain_runtime/src/index.js';

/** Shared Node composition boundary for evidence-gated crop feasibility. */
export function compareWithIntegratedSoilBrain(input) {
  return compareRotations({
    ...input,
    services: {
      ...(input.services ?? {}),
      soilBrain: createRootShiftSoilBrainService()
    }
  });
}
