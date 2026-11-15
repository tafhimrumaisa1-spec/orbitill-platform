export type EvidenceStatus = 'verified' | 'provisional' | 'unverified' | 'absent';
export type FeasibilityOutcome = 'feasible' | 'conditional' | 'infeasible' | 'insufficient_evidence' | 'unsupported';
export interface EvidenceRef { sourceId:string; title:string; url:string; geographicScope:string; retrievedDate:string; status:EvidenceStatus; note?:string; }
export interface RuleResult { ruleId:string; outcome:FeasibilityOutcome; message:string; evidence:EvidenceRef[]; missingMeasurements?:string[]; }
export interface PlantingWindow { earliest?:string; latest?:string; evidence:EvidenceRef; }
export interface CropProfile {
  cropId:string; aliases?:string[]; commonName:string; regionId:string; season:string;
  plantingWindow?:PlantingWindow; soilConstraints?:Record<string, unknown>;
  waterRequirement:'irrigation_required'|'rainfed_allowed'|'unknown';
  cropFamily?:string; durationDays?:number; rice?:boolean; legume?:boolean; isCover?:boolean;
  unsupportedFields:string[]; evidenceNotes:string[]; evidence:EvidenceRef[];
}
export interface SoilProfile {
  ph?:{value:number;source:'farmer_report'|'lab_test'|'mapped_estimate';evidence?:EvidenceRef};
  textureClass?:{value:string;source:'farmer_report'|'lab_test'|'mapped_estimate'};
  drainageClass?:{value:string;source:'farmer_report'|'lab_test'|'mapped_estimate'};
  salinityDsM?:{value:number;source:'farmer_report'|'lab_test'|'mapped_estimate';evidence?:EvidenceRef};
}
export interface EvaluateInput { regionId:string; cropId:string; proposedSowingDate:string; soil?:SoilProfile; constraints?:{waterAvailability?:'sufficient'|'limited'|'none'|'unknown'}; previousCropId?:string; }
export interface CropFeasibilityResult {
  schemaVersion:'1.0.0'; modelVersion:string; modelRunId:string; regionId:string; cropId:string;
  outcome:FeasibilityOutcome; ruleResults:RuleResult[]; missingMeasurements:string[];
  unsupportedFields:string[]; evidence:EvidenceRef[]; limitations:string[];
}
export interface RegionCropPack { regionId:string; country:string; adminRegion:string; mode:'research_pilot'|'conditional'; crops:Record<string,CropProfile>; }
export declare const MODEL_VERSION:string;
export declare const EVIDENCE:Record<string,EvidenceRef>;
export declare const PACKS:Record<string,RegionCropPack>;
export declare function getCropProfile(regionId:string,cropId:string):CropProfile|undefined;
export declare function evaluateCropFeasibility(input:EvaluateInput, crop?:CropProfile):CropFeasibilityResult;
export declare function createRootShiftSoilBrainService():{provider:string;getCropProfile:(args:any)=>any;evaluateCropFeasibility:(args:any)=>any};
