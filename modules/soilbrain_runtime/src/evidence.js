export const EVIDENCE = Object.freeze({
  BARI_WHEAT_RAJSHAHI_ARMIS: Object.freeze({
    sourceId: 'BARI_WHEAT_RAJSHAHI_ARMIS',
    title: 'BARI ARMIS wheat trial record (retrieval pending independent confirmation)',
    url: 'http://barcapps.gov.bd/armis/home/research/detail/23176',
    geographicScope: 'High Barind Tract, Rajshahi, Bangladesh; single trial/variety',
    retrievedDate: '2026-11-15',
    status: 'provisional',
    note: 'The pasted delivery reported second-half-of-November sowing for BARI Gam 21. The record was not independently retrievable during integration, so it cannot create a hard exclusion.'
  }),
  USDA_NRCS_RYE_BEFORE_SOYBEAN_IOWA: Object.freeze({
    sourceId: 'USDA_NRCS_RYE_BEFORE_SOYBEAN_IOWA',
    title: 'Using a Cover Crop Before Soybeans in an Iowa Corn-Soybean Rotation',
    url: 'https://www.nrcs.usda.gov/sites/default/files/2022-09/CoverCropBeforeSoybeans.pdf',
    geographicScope: 'Iowa, United States; cereal rye before soybean',
    retrievedDate: '2026-11-15',
    status: 'verified',
    note: 'Guide identifies cereal rye as the preferred cover crop before soybean and gives October 15 as a good target application date. It is not a universal soybean calendar.'
  }),
  USDA_NRCS_RYE_FACT_SHEET_IOWA: Object.freeze({
    sourceId: 'USDA_NRCS_RYE_FACT_SHEET_IOWA',
    title: 'Cereal Rye Cover Crop Fact Sheet for Iowa',
    url: 'https://www.nrcs.usda.gov/sites/default/files/2024-04/Cereal%20Rye%20Cover%20Crop%20Fact%20Sheet.pdf',
    geographicScope: 'Iowa, United States',
    retrievedDate: '2026-11-15',
    status: 'verified',
    note: 'Lists a general Iowa seeding period from mid-August to late October and directs users to local NRCS guidance.'
  })
});

export function uniqueEvidence(items) {
  return [...new Map(items.filter(Boolean).map(item => [item.sourceId, item])).values()];
}
