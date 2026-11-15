// EvidenceRecord registry for fixtures. `url` only where the page is a known stable reference.
// verification: 'unverified_offline' = built without network access; a human/Agent 05/06/08 must confirm before any claim.
const rec = (id, provider, title, url, role, extra = {}) => ({
  id, provider, title, url, role, license: extra.license ?? 'cite; check provider terms',
  spatialSupport: extra.spatial ?? 'n/a', temporalSupport: extra.temporal ?? 'n/a',
  transformation: extra.transform ?? 'none', dataType: extra.dataType ?? 'published reference',
  verification: extra.verification ?? 'unverified_offline', note: extra.note ?? null,
});
export const EVIDENCE = Object.fromEntries([
  rec('ev:fao56', 'FAO', 'Crop evapotranspiration — Guidelines for computing crop water requirements (Irrigation & Drainage Paper 56)', 'https://www.fao.org/4/x0490e/x0490e00.htm', 'ETc = Kc x ET0 method', { note: 'Method cited. Season-average Kc used here is a coarse simplification of the staged Kc curve.' }),
  rec('ev:fao33', 'FAO', 'Yield response to water (Irrigation & Drainage Paper 33; Doorenbos & Kassam 1979)', 'https://www.fao.org/4/i2800e/i2800e00.htm', 'Linear yield-response form Ya/Ym = 1 - Ky(1 - ETa/ETc)', { note: 'Ky values for several crops are ASSUMED placeholders; FAO-33 does not tabulate every crop used here.' }),
  rec('ev:scs-peff', 'USDA-SCS / FAO CROPWAT', 'USDA Soil Conservation Service effective-rainfall formula as implemented in CROPWAT', null, 'Monthly effective rainfall', { note: 'Specific CROPWAT manual citation to be added by Agent 06.' }),
  rec('ev:fao-cropcal', 'FAO', 'FAO Crop Calendar', 'https://cropcalendar.apps.fao.org/', 'Sowing/harvest window cross-check', { note: 'Coverage for Bangladesh crops not confirmed offline.' }),
  rec('ev:bd-local-calendar', 'BRRI / BARI / DAE (to be cited)', 'Bangladesh local crop calendars and variety durations', 'https://www.fao.org/gaez/en', 'Rajshahi sowing windows and durations', { note: 'FIXTURE window dates are typed approximations of commonly published Bangladesh calendars; Agent 05 must replace with page-level citations.' }),
  rec('ev:nasa-power', 'NASA LaRC POWER', 'POWER daily agroclimatology API', 'https://power.larc.nasa.gov/docs/services/api/temporal/daily/', 'ET0 / precipitation inputs', { dataType: 'observed (gridded meteorology)', spatial: 'about 0.5 deg grid', temporal: 'daily', note: 'NOT YET WIRED. Fixture climate below is a stand-in until Agent 04 supplies a series.' }),
  rec('ev:fixture-climate-bd', 'Typed fixture', 'Approximate Rajshahi monthly rainfall/ET0 normals (placeholder)', null, 'Stand-in climate', { dataType: 'hypothetical scenario', note: 'Not source-verified. Never present as an observation.' }),
  rec('ev:fixture-econ-bd', 'Typed fixture', 'Placeholder yields, prices, non-irrigation costs, pump cost per mm', null, 'Stand-in economics', { dataType: 'hypothetical scenario', note: 'Replace with Agent 08 values from BBS/DAE/BARI cost-of-production sources.' }),
  rec('ev:farmer-report', 'Farmer', 'Farmer-reported field inputs', null, 'Transplant date, variety duration, irrigation allowance', { dataType: 'farmer-reported', verification: 'user_supplied' }),
  rec('ev:fixture-us', 'Typed fixture', 'Iowa corn/soy/cover-crop calendar and economics placeholders', null, 'US pilot stand-in', { dataType: 'hypothetical scenario', note: 'Needs USDA NASS QuickStats / ISU Extension / USDA-CDL citations (Agent 05/08).' }),
  rec('ev:legume-n', 'Agronomy literature (to be cited)', 'Legume biological N fixation / rotation benefit', null, 'Qualitative soil indicator', { note: 'Direction of effect only; magnitude depends on field and is not quantified here.' }),
].map((r) => [r.id, r]));
