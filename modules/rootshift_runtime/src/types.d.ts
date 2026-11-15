// RootShift (Agent 07) public types. Mirrors the shared contract records; extra fields are additive.
export type DataType = 'observed' | 'farmer-reported' | 'published reference' | 'model estimate' | 'forecast' | 'hypothetical scenario';
export type CandidateStatus = 'feasible' | 'water_constrained' | 'conditional' | 'infeasible';
export type DecisionStatus = 'ok' | 'conditional' | 'refused';
export type ObjectiveKey = 'irrigationNeedMm' | 'marginWaterLimitedPerHa' | 'worstCaseMarginPerHa' | 'soilQualitativeScore';

export interface FarmProfile {
  id: string; name?: string; regionId: string;
  geometry?: unknown; area?: { value: number; unit: 'ha' | 'acre' | 'decimal' | 'bigha' };
  currentCrop?: { cropId: string; plantedOn: string | null; durationDays?: number; source: DataType } | null;
  previousCrop?: string | null;
  horizon: { start: string; end: string };            // identical for every candidate
  baselineRotation?: string[];
  soil?: { texture?: string; source?: DataType };
  irrigationAvailableMm?: number | null;               // null/undefined = unknown -> conditional
  soilWaterAtSowingMm?: number | null;
  priorities?: { water?: 'low'|'medium'|'high'; income?: 'low'|'medium'|'high'; soil?: 'low'|'medium'|'high'; riskTolerance?: 'low'|'medium'|'high' };
}
export interface Scenario {
  id: string; kind: 'baseline' | 'hypothetical scenario'; label?: string;
  rainfallMultiplier?: number; irrigationAllowanceMultiplier?: number; priceMultiplier?: number; amanTransplantDelayDays?: number;
}
export interface Reason { severity: 'blocking'|'caution'|'verify'|'info'; code: string; params: Record<string, unknown>; text: { en: string } }
export interface TimelineSlot { cropId: string; name: { en: string; bn?: string }; sow: string; harvest: string; windowEnd: string | null; slackDays: number | null; waitedDays: number; fixed: boolean; dateType: DataType }
export interface RotationResult {
  id: string; label: string; kind: 'baseline'|'template'|'enumerated'|'reference_fallow'; isBaseline: boolean; cropIds: string[];
  status: CandidateStatus; timeline: TimelineSlot[]; hardViolations: unknown[]; softWarnings: unknown[]; missing: string[];
  water: null | { status: string; irrigationNeedMm: number | null; allowanceMm: number | null; shortfallMm: number; perCrop: unknown[]; method: string };
  economics: null | { currency: string; status: string; marginWaterLimitedPerHa: number | null; marginUnconstrainedPerHa: number | null; perCrop: unknown[]; method: string };
  objectives: null | Record<ObjectiveKey, number | null>;
  objectiveMeta: Record<ObjectiveKey, { unit: string; direction: 'min'|'max'; label: string; dataType: string; uncertainty: string; basis?: string[] }>;
  robustness: null | { byScenario: Record<string, unknown>; worstCaseMarginPerHa: number | null; failedIn: string | null };
  frontier: null | { onFrontier: boolean; dominatedBy: string[] };
  reasons: Reason[]; lineage: Array<{ id: string; provider: string; title: string; url: string | null; role: string; dataType: string; verification: string; note: string | null }>;
}
export interface CompareRotationsResponse {
  schema: 'rootshift.compareRotations.v1'; modelVersion: string; inputHash: string;
  decision: { status: DecisionStatus; recommendationAllowed: boolean; conditionalOn?: string[]; reasons?: Reason[]; note: string };
  region: { id: string; readiness: Record<string, boolean>; waterModel?: string } | null; horizon: { start: string; end: string } | null;
  scenario: Scenario | null; robustnessScenarios?: unknown[];
  frontierSpec: Array<{ key: ObjectiveKey; direction: 'min'|'max'; unit: string; label: string; dataType: string }>;
  frontier: string[]; dominated: Array<{ id: string; dominatedBy: string[] }>; dominanceExamples: unknown[];
  highlights: Record<string, string | null>; highProfitConstraint: null | { id: string; status: CandidateStatus; marginUnconstrainedPerHa: number; marginWaterLimitedPerHa: number; waterConstrained: boolean };
  display: string[]; lenses: Record<'water'|'income'|'risk'|'soil', string[]>; candidates: RotationResult[];
  inputStatus: unknown; evidenceTrace: string | null; limitations: string[];
}
export interface Services {
  soilBrain: { provider: string; evaluateCropFeasibility(a: unknown): { status: string; hard: unknown[]; soft: unknown[]; missing: string[] } };
  earthSync: { provider: string; getEnvironmentalSeries(a: unknown): null | { rainMm: number[]; et0MmDay: number[]; observationType: string; evidenceId: string; intendedSource: string } };
  aquaSense: { provider: string; evaluateWaterBalance(a: unknown): unknown };
  agriEconomics: { provider: string; calculateEconomics(a: unknown): unknown };
}
export function compareRotations(input: { farm: FarmProfile; packs: Record<string, unknown>; regionPackId?: string; scenario?: Scenario; robustnessScenarios?: unknown[]; objectives?: ObjectiveKey[]; services?: Partial<Services> }): CompareRotationsResponse;
export function runScenario(input: Parameters<typeof compareRotations>[0], delta: Partial<Scenario>, label?: string): { kind: 'ModelRun'; baselineHash: string; scenarioHash: string; scenario: Scenario; diffs: unknown[]; base: CompareRotationsResponse; run: CompareRotationsResponse };
