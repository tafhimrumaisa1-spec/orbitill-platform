import { EVIDENCE } from './evidence.js';

const unsupportedSoil = ['soil.phRange', 'soil.suitableTextures', 'soil.suitableDrainage', 'salinity.tolerance'];
const blankSoil = Object.freeze({});

export const BANGLADESH_BARIND_PACK = Object.freeze({
  regionId: 'BD-RAJ-BARIND', country: 'Bangladesh', adminRegion: 'Barind Highlands, Rajshahi', mode: 'research_pilot',
  crops: Object.freeze({
    aman: Object.freeze({
      cropId: 'aman', commonName: 'Transplanted Aman rice', regionId: 'BD-RAJ-BARIND', season: 'Kharif-2', cropFamily: 'rice', rice: true,
      soilConstraints: blankSoil, waterRequirement: 'unknown', unsupportedFields: ['plantingWindow', ...unsupportedSoil, 'durationDays', 'waterRequirement'],
      evidenceNotes: ['A Barind-valid Aman calendar was not present in the pasted delivery; RootShift may expose this profile only as an evidence gap.'], evidence: []
    }),
    wheat: Object.freeze({
      cropId: 'wheat', commonName: 'Wheat (BARI Gam 21 evidence)', regionId: 'BD-RAJ-BARIND', season: 'Rabi', cropFamily: 'cereal',
      plantingWindow: { earliest: '11-15', latest: '11-30', evidence: EVIDENCE.BARI_WHEAT_RAJSHAHI_ARMIS },
      soilConstraints: blankSoil, waterRequirement: 'unknown', unsupportedFields: [...unsupportedSoil, 'durationDays', 'waterRequirement'],
      evidenceNotes: ['The reported window is provisional and variety-specific; it is guidance, not a hard boundary.'], evidence: [EVIDENCE.BARI_WHEAT_RAJSHAHI_ARMIS]
    }),
    mungbean: Object.freeze({
      cropId: 'mungbean', commonName: 'Mungbean', regionId: 'BD-RAJ-BARIND', season: 'Kharif-1', cropFamily: 'legume', legume: true,
      soilConstraints: blankSoil, waterRequirement: 'unknown', unsupportedFields: ['plantingWindow', ...unsupportedSoil, 'durationDays', 'waterRequirement'],
      evidenceNotes: ['The pasted DOI did not support the claimed Bangladesh sowing window, so no executable calendar rule is published.'], evidence: []
    }),
    mustard: Object.freeze({
      cropId: 'mustard', commonName: 'Mustard', regionId: 'BD-RAJ-BARIND', season: 'Rabi', cropFamily: 'brassica',
      soilConstraints: blankSoil, waterRequirement: 'unknown', unsupportedFields: ['plantingWindow', ...unsupportedSoil, 'durationDays', 'waterRequirement'],
      evidenceNotes: ['Evidence from Sylhet cannot be transferred to Barind without validation.'], evidence: []
    }),
    chickpea: Object.freeze({
      cropId: 'chickpea', commonName: 'Chickpea', regionId: 'BD-RAJ-BARIND', season: 'Rabi', cropFamily: 'legume', legume: true,
      soilConstraints: blankSoil, waterRequirement: 'unknown', unsupportedFields: ['plantingWindow', ...unsupportedSoil, 'durationDays', 'waterRequirement'],
      evidenceNotes: ['No Barind-valid chickpea calendar or soil threshold was present in the pasted delivery.'], evidence: []
    }),
    boro: Object.freeze({
      cropId: 'boro', aliases: ['boro-rice'], commonName: 'Boro rice', regionId: 'BD-RAJ-BARIND', season: 'Rabi (irrigated)', cropFamily: 'rice', rice: true,
      soilConstraints: blankSoil, waterRequirement: 'irrigation_required', unsupportedFields: ['plantingWindow', ...unsupportedSoil, 'durationDays'],
      evidenceNotes: ['Coastal salinity evidence is intentionally not applied to the Barind Highlands.'], evidence: []
    })
  })
});

export const IOWA_STORY_PACK = Object.freeze({
  regionId: 'US-IA-STORY', country: 'United States', adminRegion: 'Story County, Iowa', mode: 'research_pilot',
  crops: Object.freeze({
    corn: Object.freeze({ cropId:'corn', commonName:'Corn', regionId:'US-IA-STORY', season:'Summer annual', cropFamily:'grass', soilConstraints:blankSoil, waterRequirement:'rainfed_allowed', unsupportedFields:['plantingWindow', ...unsupportedSoil, 'durationDays'], evidenceNotes:['No verified Story County planting-window rule is encoded.'], evidence:[] }),
    soybean: Object.freeze({ cropId:'soybean', commonName:'Soybean', regionId:'US-IA-STORY', season:'Summer annual', cropFamily:'legume', legume:true, soilConstraints:blankSoil, waterRequirement:'rainfed_allowed', unsupportedFields:['plantingWindow', ...unsupportedSoil, 'durationDays'], evidenceNotes:['The rye guide does not establish a soybean planting window.'], evidence:[EVIDENCE.USDA_NRCS_RYE_BEFORE_SOYBEAN_IOWA] }),
    'rye_cover': Object.freeze({
      cropId:'rye_cover', aliases:['cereal-rye'], commonName:'Cereal rye cover crop', regionId:'US-IA-STORY', season:'Fall–spring cover', cropFamily:'grass', isCover:true,
      plantingWindow:{ earliest:'08-15', latest:'10-31', evidence:EVIDENCE.USDA_NRCS_RYE_FACT_SHEET_IOWA }, soilConstraints:blankSoil,
      waterRequirement:'rainfed_allowed', unsupportedFields:[...unsupportedSoil, 'durationDays'],
      evidenceNotes:['The statewide fact sheet says mid-August to late October; site-specific NRCS guidance still governs practice.'],
      evidence:[EVIDENCE.USDA_NRCS_RYE_FACT_SHEET_IOWA, EVIDENCE.USDA_NRCS_RYE_BEFORE_SOYBEAN_IOWA]
    })
  })
});

export const PACKS = Object.freeze({
  [BANGLADESH_BARIND_PACK.regionId]: BANGLADESH_BARIND_PACK,
  [IOWA_STORY_PACK.regionId]: IOWA_STORY_PACK
});

export function getCropProfile(regionId, cropId) {
  const crops = PACKS[regionId]?.crops;
  if (!crops) return undefined;
  return crops[cropId] ?? Object.values(crops).find(crop => crop.aliases?.includes(cropId));
}
