// Iowa research-pilot pack — placeholders; US rules only, no Bangladeshi crop is valid here.
export const US_REGION = {
  id: 'US-IA', iso: 'US', adminId: 'US-IA', pack: 'us_iowa', name: 'Iowa (corn/soy belt)',
  datasetAvailability: { nasa_power: 'fixture', usda_cdl: 'not_wired', quickstats: 'not_wired', farmer_input: 'live' },
  supportedCrops: ['corn', 'soybean', 'oat', 'rye_cover'], waterModel: 'not_modelled', // rainfed; RootShift refuses to invent a water axis
  readiness: { exploration: true, conditional: true, research_pilot: true, validated_with_evidence: false },
  turnaroundDays: 7, horizonLabel: 'Apr-Mar year',
};
const base = { regionIds: ['US-IA'], verification: 'unverified_offline', evidence: ['ev:fixture-us', 'ev:fao56'] };
export const US_CROPS = {
  corn:     { ...base, id: 'corn', name: { en: 'Corn' }, family: 'grass', rice: false, legume: false, window: { start: '04-20', end: '05-20' }, durationDays: 150, kc: 0.95, ky: 1.25, storageCapMm: 80, needsTexture: false },
  soybean:  { ...base, id: 'soybean', name: { en: 'Soybean' }, family: 'legume', rice: false, legume: true, window: { start: '05-05', end: '06-05' }, durationDays: 125, kc: 0.90, ky: 0.85, storageCapMm: 80, needsTexture: false },
  oat:      { ...base, id: 'oat', name: { en: 'Spring oat' }, family: 'grass', rice: false, legume: false, window: { start: '03-25', end: '04-25' }, durationDays: 95, kc: 0.85, ky: 1.0, storageCapMm: 60, needsTexture: false, kyAssumed: true },
  rye_cover:{ ...base, id: 'rye_cover', name: { en: 'Cereal rye cover crop' }, family: 'grass', rice: false, legume: false, isCover: true, window: { start: '09-15', end: '10-31' }, durationDays: 180, kc: 0.6, ky: 0, storageCapMm: 40, needsTexture: false, kyAssumed: true },
};
export const US_CLIMATE_NORMALS = {
  rainMm: [28, 30, 55, 95, 120, 135, 115, 120, 85, 70, 55, 35],
  et0MmDay: [0.6, 1.1, 2.0, 3.2, 4.4, 5.2, 5.5, 4.8, 3.4, 2.0, 1.0, 0.6],
};
export const US_ECON = {
  currency: 'USD', irrigationCostPerMmHa: 0.9, status: 'assumed_placeholder', evidence: ['ev:fixture-us'],
  crops: {
    corn: { yieldTHa: 11.0, priceBdtKg: 0.17, costBdtHa: 1500 },     // price field name reused: USD/kg
    soybean: { yieldTHa: 3.4, priceBdtKg: 0.40, costBdtHa: 850 },
    oat: { yieldTHa: 3.0, priceBdtKg: 0.28, costBdtHa: 600 },
    rye_cover: { yieldTHa: 0, priceBdtKg: 0, costBdtHa: 90 },
  },
};
export const US_PACK = { region: US_REGION, crops: US_CROPS, climate: US_CLIMATE_NORMALS, economics: US_ECON, templates: [['corn'], ['corn', 'rye_cover'], ['soybean', 'rye_cover'], ['oat', 'rye_cover']], defaultBaseline: ['corn'], referenceFallow: [] };
export const SAMPLE_FARM_US = {
  id: 'farm:us-ia-sample-01', name: 'Sample farm: Story County plot (fictional)', regionId: 'US-IA',
  geometry: { type: 'Point', coordinates: [-93.6, 42.03] }, area: { value: 40, unit: 'ha' },
  currentCrop: null, previousCrop: 'soybean',
  horizon: { start: '2026-04-15', end: '2027-04-14' },
  baselineRotation: ['corn'], soil: { texture: 'silty_clay_loam', source: 'farmer-reported' },
  irrigationAvailableMm: 0, priorities: { water: 'low', income: 'high', soil: 'high', riskTolerance: 'medium' },
};
