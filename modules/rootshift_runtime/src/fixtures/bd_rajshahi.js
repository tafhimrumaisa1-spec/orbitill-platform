// Rajshahi (Barind) region pack — ALL NUMBERS ARE TYPED PLACEHOLDERS (see EVIDENCE verification flags).
// Owners who must replace them: crops/calendar -> Agent 05 (SoilBrain); climate -> Agent 04 (EarthSync);
// water method -> Agent 06 (AquaSense); economics -> Agent 08 (AgriEconomics).
export const BD_REGION = {
  id: 'BD-RAJ', iso: 'BD', adminId: 'BD-RAJSHAHI', pack: 'bd_rajshahi', name: 'Rajshahi / Barind Tract',
  datasetAvailability: { nasa_power: 'fixture', smap: 'not_used', hls_ndvi: 'not_used', farmer_input: 'live' },
  supportedCrops: ['aman', 'boro', 'wheat', 'chickpea', 'mustard', 'mungbean'],
  readiness: { exploration: true, conditional: true, research_pilot: true, validated_with_evidence: false },
  waterModel: 'supported', turnaroundDays: 5, horizonLabel: 'Jul-Jun agricultural year',
};
const base = { regionIds: ['BD-RAJ'], verification: 'unverified_offline' };
export const BD_CROPS = {
  aman:     { ...base, id: 'aman', name: { en: 'T. Aman rice', bn: 'রোপা আমন' }, family: 'rice', rice: true, legume: false, window: { start: '07-10', end: '08-20' }, durationDays: 120, kc: 1.10, ky: 1.09, landPrepMm: 150, percMmPerDay: 2, storageCapMm: 100, evidence: ['ev:bd-local-calendar', 'ev:fao56', 'ev:fao33'], needsTexture: false },
  boro:     { ...base, id: 'boro', name: { en: 'Boro rice', bn: 'বোরো ধান' }, family: 'rice', rice: true, legume: false, window: { start: '01-10', end: '02-15' }, durationDays: 140, kc: 1.10, ky: 1.09, landPrepMm: 150, percMmPerDay: 2, storageCapMm: 100, evidence: ['ev:bd-local-calendar', 'ev:fao56', 'ev:fao33'], needsTexture: false },
  wheat:    { ...base, id: 'wheat', name: { en: 'Wheat', bn: 'গম' }, family: 'cereal', rice: false, legume: false, window: { start: '11-15', end: '12-15' }, durationDays: 105, kc: 0.90, ky: 1.15, storageCapMm: 40, evidence: ['ev:bd-local-calendar', 'ev:fao56', 'ev:fao33'], needsTexture: false },
  chickpea: { ...base, id: 'chickpea', name: { en: 'Chickpea', bn: 'ছোলা' }, family: 'legume', rice: false, legume: true, window: { start: '11-10', end: '12-10' }, durationDays: 105, kc: 0.80, ky: 0.90, storageCapMm: 40, evidence: ['ev:bd-local-calendar', 'ev:fao56', 'ev:legume-n'], needsTexture: true, kyAssumed: true },
  mustard:  { ...base, id: 'mustard', name: { en: 'Mustard', bn: 'সরিষা' }, family: 'brassica', rice: false, legume: false, window: { start: '10-25', end: '11-25' }, durationDays: 90, kc: 0.90, ky: 0.90, storageCapMm: 40, evidence: ['ev:bd-local-calendar', 'ev:fao56'], needsTexture: false, kyAssumed: true },
  mungbean: { ...base, id: 'mungbean', name: { en: 'Mungbean (summer)', bn: 'মুগডাল' }, family: 'legume', rice: false, legume: true, window: { start: '03-01', end: '04-15' }, durationDays: 62, kc: 0.85, ky: 1.00, storageCapMm: 40, evidence: ['ev:bd-local-calendar', 'ev:fao56', 'ev:legume-n'], needsTexture: false, kyAssumed: true },
};
// Monthly climatology stand-in (mm/month rain, mm/day ET0). Approximate; NOT an observation.
export const BD_CLIMATE_NORMALS = {
  rainMm: [8, 15, 25, 55, 150, 270, 330, 280, 250, 110, 15, 5],
  et0MmDay: [2.0, 2.9, 4.2, 5.4, 5.6, 4.6, 4.0, 4.0, 3.8, 3.4, 2.6, 2.0],
};
export const BD_ECON = {
  currency: 'BDT', irrigationCostPerMmHa: 12, status: 'assumed_placeholder', evidence: ['ev:fixture-econ-bd'],
  crops: {
    aman: { yieldTHa: 3.6, priceBdtKg: 28, costBdtHa: 65000 },
    boro: { yieldTHa: 5.0, priceBdtKg: 28, costBdtHa: 85000 },
    wheat: { yieldTHa: 2.8, priceBdtKg: 35, costBdtHa: 58000 },
    chickpea: { yieldTHa: 1.1, priceBdtKg: 90, costBdtHa: 45000 },
    mustard: { yieldTHa: 1.2, priceBdtKg: 80, costBdtHa: 40000 },
    mungbean: { yieldTHa: 0.9, priceBdtKg: 90, costBdtHa: 32000 },
  },
};
export const BD_TEMPLATES = [
  ['aman', 'boro'], ['aman', 'wheat', 'mungbean'], ['aman', 'chickpea', 'mungbean'],
  ['aman', 'mustard', 'mungbean'], ['aman', 'mustard', 'boro'], ['aman', 'wheat', 'boro'],
];
export const BD_PACK = { region: BD_REGION, crops: BD_CROPS, climate: BD_CLIMATE_NORMALS, economics: BD_ECON, templates: BD_TEMPLATES, defaultBaseline: ['aman', 'boro'], referenceFallow: ['aman'] };

/** Named sample farm "Rahim Mia, Godagari, Rajshahi" — fictional, for demo only. */
export const SAMPLE_FARM_BD = {
  id: 'farm:bd-raj-sample-01', name: 'Sample farm: Godagari plot (fictional)', regionId: 'BD-RAJ',
  geometry: { type: 'Point', coordinates: [88.35, 24.45] }, area: { value: 0.4, unit: 'ha' },
  currentCrop: { cropId: 'aman', plantedOn: '2026-07-25', source: 'farmer-reported' },
  horizon: { start: '2026-07-01', end: '2027-06-30' },
  baselineRotation: ['aman', 'boro'],
  soil: { texture: 'clay_loam', source: 'farmer-reported' },
  irrigationAvailableMm: 700, // annual groundwater allowance (mm over the field) — farmer-reported PLACEHOLDER
  priorities: { water: 'high', income: 'medium', soil: 'medium', riskTolerance: 'low' },
};
