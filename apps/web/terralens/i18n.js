/* Interface strings. English is the source of truth; Bangla mirrors it.
   Server-supplied scientific prose (caveats, limitations, dataset descriptions)
   is returned in English by the router and is displayed as source text. */

const EN = {
  // chrome
  eyebrow: "NASA Space Apps · ORBITILL / RootShift",
  headline: "Read the ground.<br><em>Know the limits.</em>",
  lede: "A regional lens on real geography. Boundaries, NASA products and their native footprints — with the evidence that is missing said out loud.",
  pilots: "Pilot regions",
  pilotsNote: "one click",
  search: "Find a place",
  searchLabel: "Search divisions, districts, upazilas, counties or countries",
  searchPlaceholder: "District, upazila, county, country…",
  go: "Go",
  lat: "Latitude",
  lon: "Longitude",
  locate: "Locate",
  useCentre: "Use map centre",
  coordNote: "WGS84 decimal degrees. A point is a location, not a field boundary.",
  context: "Selected context",
  farmer: "Open in Farmer Mode",
  railFoot: "Offline-first boundaries · optional NASA GIBS raster tiles · no API key, no tracking.",
  draw: "Draw field",
  grids: "Native grids",
  drawHint: "Click to place corners. Double-click or press Enter to close. Esc cancels.",
  finish: "Finish",
  cancel: "Cancel",
  tabRegion: "Region",
  tabField: "Field",
  tabLayers: "Layers",
  tabSources: "Sources",
  legendTitle: "Legend",
  legendDefaultName: "Administrative boundaries",
  legendModeBoundaries: "boundaries",
  attribution: "Boundaries: geoBoundaries, Natural Earth",
  staticBadge: "static atlas",
  liveBadge: "live map",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  drawTitle: "Draw a field boundary",
  gridsTitle: "Show native grid footprints",
  aboutBtn: "About this instrument",
  mapLabel: "Map of administrative boundaries and NASA layers",
  aboutClose: "Close",
  sourceUsedHere: "used here",
  sourcesCount: "{n} sources",
  chipNoFarmClaims: "no farm-level claims",
  chipCropRules: "crop rules: SoilBrain",
  chipBoundaries: "cartographic boundaries",
  farmerHandoffNote: "Opens the working conditional Barind comparison with this regional context.",
  farmerDisabledNote: "Farmer Mode needs a supported region pack on land.",
  boundaryNote: "Cartographic boundaries, not cadastral. Pilot extents are administrative proxies.",
  toastStaticRaster: "The static atlas draws boundaries only. The legend still shows this layer's native resolution and units.",
  fieldStaticDisabled: "Drawing needs the live map; the static atlas can still select a point.",

  // readiness / availability
  readinessTitle: "Readiness by analysis",
  readinessNote: "Capped by the selected region pack. Owner services perform the actual computation.",
  limitsTitle: "Limitations",
  missingTitle: "Missing requirements",
  unknownTitle: "Typed unknowns",
  datasetTitle: "Datasets advertised",
  datasetFootprint: "Footprint",
  datasetAccess: "Access",
  footprintTitle: "Grid footprints at this point",
  footprintNote: "Drawn from each product's own grid convention. A cell value belongs to the whole cell, never to a farm inside it.",
  modeResearchPilot: "research pilot",
  modeConditional: "conditional",
  modeExploration: "exploration",
  modeValidated: "validated with evidence",
  availAvailable: "available",
  availConditional: "conditional",
  availRequiresInput: "input required",
  availBlocked: "blocked",
  availNotScoped: "not scoped",
  owner: "Owner",
  missing: "Missing",
  sourceNeeded: "Source needed",
  unknownState: "state",
  noAdmin: "No administrative unit assigned",
  adminUnit: "Administrative unit",

  // facts
  factCountry: "Country",
  factDivision: "Division",
  factDistrict: "District",
  factUpazila: "Upazila",
  factMode: "Mode",
  factPilot: "Pilot extent",
  factArea: "Area",
  factReadiness: "Readiness cap",
  factDepth: "Admin depth",
  factNearest: "Nearest land",
  factPoint: "Point",
  factCode: "Code",
  factStats: "Stats",
  inPilot: "inside pilot",
  outsidePilot: "outside pilot",
  kmAway: "{n} km away",
  unitsKm2: "km²",

  // search levels
  levelCountry: "country",
  levelDivision: "division",
  levelDistrict: "district",
  levelUpazila: "upazila / thana",
  levelCounty: "county",
  levelState: "state",
  searchEmpty: "No matching place in the bundled boundaries.",
  searchHint: "Type at least two characters.",
  searching: "Searching…",
  searchOffline: "Search needs the local API server.",

  // field
  fieldEyebrow: "Farm selection",
  fieldTitle: "A boundary you draw is not a survey",
  fieldIntro: "Draw a field on the map, or select an approximate point. Area is computed on a sphere. Footprints show how small the field is next to each native product.",
  fieldDraw: "Draw field boundary",
  fieldUsePoint: "Use selected point",
  fieldClear: "Clear",
  fieldEmptyTitle: "No field selected yet",
  fieldEmptyBody: "Draw a boundary on the map, or select the current point. Both are user input, not survey evidence.",
  fieldArea: "Area",
  fieldPerimeter: "Perimeter",
  fieldPrecision: "Precision",
  fieldRegion: "Region resolved",
  fieldPolygon: "Drawn polygon",
  fieldPointApprox: "Approximate point",
  fieldHectares: "ha",
  fieldAcres: "acres",
  fieldFootprintTitle: "Scale against native products",
  fieldFootprintNote: "The red mark is the field at the same scale as one native cell. Most fields are a speck.",
  fieldNoFootprints: "A point has no area, so no footprint share can be computed.",
  fieldRefused: "Selection refused",
  fieldShare: "{pct}% of one cell",
  fieldPixels: "≈{n} pixels",
  fieldPointNote: "A point has no area. Draw a polygon for footprint comparisons.",

  // layers
  layersEyebrow: "Map layers",
  layersTitle: "One environmental layer at a time",
  layersIntro: "Every layer keeps its native resolution and time step. The legend repeats the unit, cadence and footprint so the map cannot quietly imply farm-level measurement.",
  envLayer: "Environmental layer",
  overlays: "Overlays",
  baseLayers: "Boundary base",
  layerNoneTitle: "No environmental layer",
  layerNoneMeta: "Boundaries, pilot extents and native grids only",
  layerUnits: "Unit",
  layerNative: "Native",
  layerCadence: "Cadence",
  layerOffline: "offline",
  layerOnline: "online",
  layerScaleNote: "Scale aid",
  overlayGrids: "Native grid footprints at the selected point",
  overlayGridsMeta: "NASA POWER, IMERG and a nominal 9 km SMAP square",
  overlayPilots: "Pilot extents",
  overlayPilotsMeta: "Barind and coastal administrative proxies",
  overlayPoints: "Selected point and field",
  overlayPointsMeta: "User input, never evidence",
  date: "Observation date (UTC)",
  latest: "Latest",
  dateNote: "The date is sent to NASA GIBS. Fixed dates lag by the product's latency; a blank tile means no usable observation.",
  dateStatic: "This layer is static; the date selector does not apply.",
  attributionGibs: "NASA GIBS / NASA EOSDIS · boundaries: geoBoundaries, Natural Earth",

  // sources
  sourcesEyebrow: "Evidence trail",
  sourcesTitle: "Sources, licences and limits",
  sourcesIntro: "Every advertised layer maps to a registered source. Downloaded boundaries carry a SHA-256. Advertised services name the owning module.",
  sourceFilter: "Filter sources…",
  sourceLicense: "Licence",
  sourceRetrieved: "retrieved {date}",
  sourceUsed: "Used for",
  sourceSha: "SHA-256",
  noSources: "No source matches this filter.",

  // notices / toasts
  offlineTitle: "Raster tiles are offline.",
  offlineBody: "The vector atlas and all region logic still work.",
  offlineTitleNoNet: "You are offline.",
  offlineBodyNoNet: "Boundaries and routing still work from the local bundle.",
  tileFailTitle: "NASA tiles did not load.",
  tileFailBody: "Check the network, or keep using the vector atlas. No values are fabricated.",
  boundaryFailTitle: "A boundary file did not load.",
  boundaryFailBody: "The bundled GeoJSON is unavailable; the rest of the instrument still works.",
  toastStatic: "Static atlas: WebGL is unavailable, so the SVG atlas is used. Selection, grids and search still work.",
  toastDrawOn: "Draw mode: click each corner, then Finish or Enter.",
  toastDrawOff: "Draw mode cancelled.",
  toastNeedThree: "A field needs at least three corners.",
  toastFieldReady: "Field measured on a sphere. This is a drawn boundary, not a survey.",
  toastFieldRefused: "The selection was refused. See the typed reasons in the Field panel.",
  toastCopied: "Link copied to the clipboard.",
  toastCopyFailed: "Could not copy the link. Select it from the address bar.",
  toastFarmer: "Farmer Mode link prepared. The /farmer route is delivered by the Farmer Mode module.",
  toastSearchFail: "Search is unavailable. The local API server may have stopped.",
  toastProfileFail: "The region profile could not be loaded.",
  toastLocale: "Interface language changed. Scientific source text stays in English.",
  toastDate: "Date applied. Blank areas are missing observations, not zeros.",
  toastGridsOn: "Native grid footprints shown at the selected point.",
  toastGridsOff: "Native grid footprints hidden.",
  toastPoint: "Point selected. Draw a boundary to measure area.",
  toastNoLayer: "Environmental layer removed; boundaries remain.",
  docTitle: "TerraLens · Region Explorer",
  loading: "Loading the boundary bundle…",
  retry: "Retry",
  errorTitle: "The instrument could not start",
  errorBody: "The local API did not answer. Start it with: python3 -m terralens serve",
  staticNote: "Static atlas · pan and zoom with the buttons, or drag. Click to select a point.",

  // about
  aboutEyebrow: "About",
  aboutTitle: "What this instrument does — and refuses to do",
  aboutP1: "TerraLens resolves a coordinate or place to a country, an administrative chain and a regional readiness state. It selects which NASA products may inform an analysis and states their native footprint. It does not fetch environmental values, store crop rules or validate farms.",
  aboutLi1: "<strong>Boundaries</strong> are cartographic: geoBoundaries (CC0 / CC BY 3.0 IGO) and Natural Earth (public domain). They are not cadastral.",
  aboutLi2: "<strong>NASA layers</strong> are gridded or image products. An SMAP 9 km cell, an IMERG 11 km cell and a 30 m HLS pixel are not measurements of a field.",
  aboutLi3: "<strong>Readiness</strong> stops at <code>research_pilot</code>. <code>validated_with_evidence</code> exists in the shared contract but is never emitted here.",
  aboutLi4: "<strong>Ownership</strong>: EarthSync fetches environmental series, SoilBrain owns crop and soil rules, AquaSense owns water state, RootShift compares rotations, FutureFields computes economics.",
  aboutFine: "No API keys. No analytics. Optional raster tiles come directly from NASA GIBS. MapLibre GL JS 6.18.0 (BSD-3-Clause) is vendored locally. Scientific source text is English-only in this build; the interface language is independent of the selected country.",
};

const BN = {
  eyebrow: "নাসা স্পেস অ্যাপস · অরবিটিল / রুটশিফট",
  headline: "ভূমি পড়ুন।<br><em>সীমা জানুন।</em>",
  lede: "বাস্তব ভূগোলের আঞ্চলিক দৃষ্টি। সীমানা, নাসার পণ্য ও তাদের নিজস্ব ফুটপ্রিন্ট — আর কোন প্রমাণ অনুপস্থিত, তা স্পষ্ট করে বলা হয়।",
  pilots: "পাইলট অঞ্চল",
  pilotsNote: "এক ক্লিকে",
  search: "স্থান খুঁজুন",
  searchLabel: "বিভাগ, জেলা, উপজেলা, কাউন্টি বা দেশ খুঁজুন",
  searchPlaceholder: "জেলা, উপজেলা, কাউন্টি, দেশ…",
  go: "যান",
  lat: "অক্ষাংশ",
  lon: "দ্রাঘিমাংশ",
  locate: "অবস্থান",
  useCentre: "মানচিত্রের কেন্দ্র",
  coordNote: "WGS84 দশমিক ডিগ্রি। একটি বিন্দু একটি অবস্থান, মাঠের সীমানা নয়।",
  context: "নির্বাচিত প্রেক্ষাপট",
  farmer: "কৃষক মোডে খুলুন",
  railFoot: "অফলাইন-প্রথম সীমানা · ঐচ্ছিক নাসা GIBS র‍্যাস্টার · কোনো API কী নেই, কোনো ট্র্যাকিং নেই।",
  draw: "মাঠ আঁকুন",
  grids: "নেটিভ গ্রিড",
  drawHint: "কোণা বসাতে ক্লিক করুন। দ্বি-ক্লিক বা Enter দিয়ে বন্ধ করুন। Esc বাতিল করে।",
  finish: "শেষ",
  cancel: "বাতিল",
  tabRegion: "অঞ্চল",
  tabField: "মাঠ",
  tabLayers: "স্তর",
  tabSources: "উৎস",
  legendTitle: "লেজেন্ড",
  legendDefaultName: "প্রশাসনিক সীমানা",
  legendModeBoundaries: "সীমানা",
  attribution: "সীমানা: geoBoundaries, Natural Earth",
  staticBadge: "স্থির অ্যাটলাস",
  liveBadge: "সক্রিয় মানচিত্র",
  zoomIn: "জুম ইন",
  zoomOut: "জুম আউট",
  drawTitle: "মাঠের সীমানা আঁকুন",
  gridsTitle: "নেটিভ গ্রিড ফুটপ্রিন্ট দেখান",
  aboutBtn: "এই যন্ত্র সম্পর্কে",
  mapLabel: "প্রশাসনিক সীমানা ও নাসা স্তরের মানচিত্র",
  aboutClose: "বন্ধ করুন",
  sourceUsedHere: "এখানে ব্যবহৃত",
  sourcesCount: "{n} উৎস",
  chipNoFarmClaims: "খামার-পর্যায়ের দাবি নেই",
  chipCropRules: "শস্য-নিয়ম: SoilBrain",
  chipBoundaries: "কার্টোগ্রাফিক সীমানা",
  farmerHandoffNote: "এই আঞ্চলিক প্রেক্ষাপটসহ কার্যকর শর্তাধীন বরেন্দ্র তুলনা খুলে।",
  farmerDisabledNote: "কৃষক মোডের জন্য স্থলে একটি সমর্থিত অঞ্চল প্যাক প্রয়োজন।",
  boundaryNote: "কার্টোগ্রাফিক সীমানা, ক্যাডাস্ট্রাল নয়। পাইলট সীমা প্রশাসনিক প্রক্সি।",
  toastStaticRaster: "স্থির অ্যাটলাস শুধু সীমানা আঁকে। লেজেন্ড এখনো এই স্তরের নেটিভ রেজোলিউশন ও একক দেখায়।",
  fieldStaticDisabled: "আঁকার জন্য সক্রিয় মানচিত্র প্রয়োজন; স্থির অ্যাটলাসে বিন্দু নির্বাচন করা যায়।",

  readinessTitle: "বিশ্লেষণ অনুযায়ী প্রস্তুতি",
  readinessNote: "নির্বাচিত অঞ্চল প্যাক দ্বারা সীমাবদ্ধ। প্রকৃত গণনা মালিকানাধীন সেবা সম্পাদন করে।",
  limitsTitle: "সীমাবদ্ধতা",
  missingTitle: "অনুপস্থিত প্রয়োজনীয়তা",
  unknownTitle: "টাইপকৃত অজানা",
  datasetTitle: "ঘোষিত ডেটাসেট",
  datasetFootprint: "ফুটপ্রিন্ট",
  datasetAccess: "প্রবেশাধিকার",
  footprintTitle: "এই বিন্দুতে গ্রিড ফুটপ্রিন্ট",
  footprintNote: "প্রতিটি পণ্যের নিজস্ব গ্রিড নিয়ম থেকে আঁকা। একটি সেলের মান পুরো সেলের, ভিতরের কোনো খামারের নয়।",
  modeResearchPilot: "গবেষণা পাইলট",
  modeConditional: "শর্তাধীন",
  modeExploration: "অন্বেষণ",
  modeValidated: "প্রমাণসহ যাচাইকৃত",
  availAvailable: "উপলব্ধ",
  availConditional: "শর্তাধীন",
  availRequiresInput: "ইনপুট প্রয়োজন",
  availBlocked: "অবরুদ্ধ",
  availNotScoped: "এখানে অন্তর্ভুক্ত নয়",
  owner: "মালিক",
  missing: "অনুপস্থিত",
  sourceNeeded: "প্রয়োজনীয় উৎস",
  unknownState: "অবস্থা",
  noAdmin: "কোনো প্রশাসনিক ইউনিট নির্ধারিত হয়নি",
  adminUnit: "প্রশাসনিক ইউনিট",

  factCountry: "দেশ",
  factDivision: "বিভাগ",
  factDistrict: "জেলা",
  factUpazila: "উপজেলা",
  factMode: "মোড",
  factPilot: "পাইলট সীমা",
  factArea: "আয়তন",
  factReadiness: "প্রস্তুতি সীমা",
  factDepth: "প্রশাসনিক গভীরতা",
  factNearest: "নিকটতম ভূমি",
  factPoint: "বিন্দু",
  factCode: "কোড",
  factStats: "পরিসংখ্যান",
  inPilot: "পাইলটের ভিতরে",
  outsidePilot: "পাইলটের বাইরে",
  kmAway: "{n} কিমি দূরে",
  unitsKm2: "বর্গকিমি",

  levelCountry: "দেশ",
  levelDivision: "বিভাগ",
  levelDistrict: "জেলা",
  levelUpazila: "উপজেলা / থানা",
  levelCounty: "কাউন্টি",
  levelState: "অঙ্গরাজ্য",
  searchEmpty: "সংযুক্ত সীমানায় কোনো মিল পাওয়া যায়নি।",
  searchHint: "অন্তত দুই অক্ষর লিখুন।",
  searching: "খোঁজা হচ্ছে…",
  searchOffline: "অনুসন্ধানের জন্য স্থানীয় API সার্ভার প্রয়োজন।",

  fieldEyebrow: "খামার নির্বাচন",
  fieldTitle: "আপনার আঁকা সীমানা জরিপ নয়",
  fieldIntro: "মানচিত্রে একটি মাঠ আঁকুন, অথবা আনুমানিক বিন্দু নির্বাচন করুন। আয়তন গোলকে গণনা করা হয়। ফুটপ্রিন্ট দেখায় প্রতিটি নেটিভ পণ্যের তুলনায় মাঠটি কত ছোট।",
  fieldDraw: "মাঠের সীমানা আঁকুন",
  fieldUsePoint: "নির্বাচিত বিন্দু ব্যবহার করুন",
  fieldClear: "মুছুন",
  fieldEmptyTitle: "এখনো কোনো মাঠ নির্বাচিত হয়নি",
  fieldEmptyBody: "মানচিত্রে সীমানা আঁকুন, অথবা বর্তমান বিন্দু নির্বাচন করুন। দুটোই ব্যবহারকারীর ইনপুট, জরিপের প্রমাণ নয়।",
  fieldArea: "আয়তন",
  fieldPerimeter: "পরিসীমা",
  fieldPrecision: "নিখুঁততা",
  fieldRegion: "নির্ধারিত অঞ্চল",
  fieldPolygon: "আঁকা বহুভুজ",
  fieldPointApprox: "আনুমানিক বিন্দু",
  fieldHectares: "হেক্টর",
  fieldAcres: "একর",
  fieldFootprintTitle: "নেটিভ পণ্যের সঙ্গে স্কেল",
  fieldFootprintNote: "লাল চিহ্নটি একটি নেটিভ সেলের সমান স্কেলে মাঠ। বেশিরভাগ মাঠ এক বিন্দুর সমান।",
  fieldNoFootprints: "বিন্দুর আয়তন নেই, তাই ফুটপ্রিন্টের অংশ গণনা করা যায় না।",
  fieldRefused: "নির্বাচন প্রত্যাখ্যাত",
  fieldShare: "এক সেলের {pct}%",
  fieldPixels: "≈{n} পিক্সেল",
  fieldPointNote: "বিন্দুর আয়তন নেই। ফুটপ্রিন্ট তুলনার জন্য বহুভুজ আঁকুন।",

  layersEyebrow: "মানচিত্র স্তর",
  layersTitle: "একবারে একটি পরিবেশগত স্তর",
  layersIntro: "প্রতিটি স্তর নিজস্ব রেজোলিউশন ও সময়-ধাপ ধরে রাখে। লেজেন্ড একক, ছন্দ ও ফুটপ্রিন্ট পুনরাবৃত্তি করে, যাতে মানচিত্র চুপচাপ খামার-পর্যায়ের মাপ বোঝাতে না পারে।",
  envLayer: "পরিবেশগত স্তর",
  overlays: "ওভারলে",
  baseLayers: "সীমানা ভিত্তি",
  layerNoneTitle: "কোনো পরিবেশগত স্তর নয়",
  layerNoneMeta: "শুধু সীমানা, পাইলট সীমা ও নেটিভ গ্রিড",
  layerUnits: "একক",
  layerNative: "নেটিভ",
  layerCadence: "ছন্দ",
  layerOffline: "অফলাইন",
  layerOnline: "অনলাইন",
  layerScaleNote: "স্কেল সহায়ক",
  overlayGrids: "নির্বাচিত বিন্দুতে নেটিভ গ্রিড ফুটপ্রিন্ট",
  overlayGridsMeta: "নাসা POWER, IMERG এবং আনুমানিক ৯ কিমি SMAP বর্গ",
  overlayPilots: "পাইলট সীমা",
  overlayPilotsMeta: "বরেন্দ্র ও উপকূলীয় প্রশাসনিক প্রক্সি",
  overlayPoints: "নির্বাচিত বিন্দু ও মাঠ",
  overlayPointsMeta: "ব্যবহারকারীর ইনপুট, কখনো প্রমাণ নয়",
  date: "পর্যবেক্ষণ তারিখ (UTC)",
  latest: "সর্বশেষ",
  dateNote: "তারিখটি নাসা GIBS-এ পাঠানো হয়। নির্দিষ্ট তারিখ পণ্যের বিলম্ব অনুযায়ী পিছিয়ে থাকে; ফাঁকা টাইল মানে ব্যবহারযোগ্য পর্যবেক্ষণ নেই।",
  dateStatic: "এই স্তরটি স্থির; তারিখ নির্বাচক প্রযোজ্য নয়।",
  attributionGibs: "নাসা GIBS / নাসা EOSDIS · সীমানা: geoBoundaries, Natural Earth",

  sourcesEyebrow: "প্রমাণের সূত্র",
  sourcesTitle: "উৎস, লাইসেন্স ও সীমা",
  sourcesIntro: "প্রতিটি ঘোষিত স্তর একটি নিবন্ধিত উৎসের সঙ্গে যুক্ত। ডাউনলোড করা সীমানার SHA-256 আছে। ঘোষিত সেবাগুলো তাদের মালিক মডিউল উল্লেখ করে।",
  sourceFilter: "উৎস ফিল্টার করুন…",
  sourceLicense: "লাইসেন্স",
  sourceRetrieved: "{date}-এ সংগৃহীত",
  sourceUsed: "যে কাজে ব্যবহৃত",
  sourceSha: "SHA-256",
  noSources: "এই ফিল্টারে কোনো উৎস মেলে না।",

  offlineTitle: "র‍্যাস্টার টাইল অফলাইন।",
  offlineBody: "ভেক্টর অ্যাটলাস ও সব অঞ্চল-লজিক এখনো কাজ করে।",
  offlineTitleNoNet: "আপনি অফলাইনে আছেন।",
  offlineBodyNoNet: "স্থানীয় বান্ডল থেকে সীমানা ও রাউটিং এখনো কাজ করে।",
  tileFailTitle: "নাসার টাইল লোড হয়নি।",
  tileFailBody: "নেটওয়ার্ক দেখুন, অথবা ভেক্টর অ্যাটলাস ব্যবহার চালিয়ে যান। কোনো মান বানানো হয় না।",
  boundaryFailTitle: "একটি সীমানা ফাইল লোড হয়নি।",
  boundaryFailBody: "সংযুক্ত GeoJSON পাওয়া যাচ্ছে না; যন্ত্রের বাকি অংশ এখনো কাজ করে।",
  toastStatic: "স্থির অ্যাটলাস: WebGL নেই, তাই SVG অ্যাটলাস ব্যবহৃত হচ্ছে। নির্বাচন, গ্রিড ও অনুসন্ধান এখনো কাজ করে।",
  toastDrawOn: "আঁকা মোড: প্রতিটি কোণায় ক্লিক করুন, তারপর শেষ বা Enter চাপুন।",
  toastDrawOff: "আঁকা মোড বাতিল হয়েছে।",
  toastNeedThree: "একটি মাঠে অন্তত তিনটি কোণা প্রয়োজন।",
  toastFieldReady: "গোলকে মাঠ মাপা হয়েছে। এটি আঁকা সীমানা, জরিপ নয়।",
  toastFieldRefused: "নির্বাচন প্রত্যাখ্যান করা হয়েছে। মাঠ প্যানেলে টাইপকৃত কারণ দেখুন।",
  toastCopied: "লিংক ক্লিপবোর্ডে কপি হয়েছে।",
  toastCopyFailed: "লিংক কপি করা যায়নি। ঠিকানার বার থেকে নির্বাচন করুন।",
  toastFarmer: "কৃষক মোডের লিংক প্রস্তুত। /farmer রুট কৃষক মোড মডিউল সরবরাহ করে।",
  toastSearchFail: "অনুসন্ধান পাওয়া যাচ্ছে না। স্থানীয় API সার্ভার বন্ধ হতে পারে।",
  toastProfileFail: "অঞ্চল প্রোফাইল লোড করা যায়নি।",
  toastLocale: "ইন্টারফেসের ভাষা বদলেছে। বৈজ্ঞানিক উৎস-পাঠ ইংরেজিতে থাকবে।",
  toastDate: "তারিখ প্রয়োগ হয়েছে। ফাঁকা অংশ মানে অনুপস্থিত পর্যবেক্ষণ, শূন্য নয়।",
  toastGridsOn: "নির্বাচিত বিন্দুতে নেটিভ গ্রিড ফুটপ্রিন্ট দেখানো হচ্ছে।",
  toastGridsOff: "নেটিভ গ্রিড ফুটপ্রিন্ট লুকানো হয়েছে।",
  toastPoint: "বিন্দু নির্বাচিত। আয়তন মাপতে সীমানা আঁকুন।",
  toastNoLayer: "পরিবেশগত স্তর সরানো হয়েছে; সীমানা থাকছে।",
  docTitle: "টেরালেন্স · অঞ্চল অন্বেষক",
  loading: "সীমানা বান্ডল লোড হচ্ছে…",
  retry: "আবার চেষ্টা",
  errorTitle: "যন্ত্রটি চালু করা যায়নি",
  errorBody: "স্থানীয় API উত্তর দেয়নি। এটি চালু করুন: python3 -m terralens serve",
  staticNote: "স্থির অ্যাটলাস · বোতাম দিয়ে জুম করুন, অথবা টেনে সরান। বিন্দু নির্বাচনে ক্লিক করুন।",

  aboutEyebrow: "পরিচিতি",
  aboutTitle: "এই যন্ত্র যা করে — এবং যা করতে অস্বীকার করে",
  aboutP1: "টেরালেন্স একটি স্থানাঙ্ক বা স্থানকে দেশ, প্রশাসনিক শৃঙ্খল ও আঞ্চলিক প্রস্তুতি-অবস্থায় রূপান্তর করে। কোন নাসা পণ্য একটি বিশ্লেষণে সহায়ক হতে পারে তা বেছে নেয় এবং তাদের নেটিভ ফুটপ্রিন্ট বলে। এটি পরিবেশগত মান আনে না, শস্য-নিয়ম সংরক্ষণ করে না, খামার যাচাই করে না।",
  aboutLi1: "<strong>সীমানা</strong> কার্টোগ্রাফিক: geoBoundaries (CC0 / CC BY 3.0 IGO) ও Natural Earth (পাবলিক ডোমেইন)। এগুলো ক্যাডাস্ট্রাল নয়।",
  aboutLi2: "<strong>নাসা স্তর</strong> গ্রিড বা চিত্র-পণ্য। একটি ৯ কিমি SMAP সেল, একটি ১১ কিমি IMERG সেল এবং একটি ৩০ মিটার HLS পিক্সেল কোনো মাঠের মাপ নয়।",
  aboutLi3: "<strong>প্রস্তুতি</strong> <code>research_pilot</code>-এ থেমে যায়। <code>validated_with_evidence</code> শেয়ার্ড চুক্তিতে আছে, কিন্তু এখান থেকে কখনো প্রকাশ করা হয় না।",
  aboutLi4: "<strong>মালিকানা</strong>: EarthSync পরিবেশগত সিরিজ আনে, SoilBrain শস্য ও মাটি-নিয়মের মালিক, AquaSense পানির অবস্থার মালিক, RootShift আবর্তন তুলনা করে, FutureFields অর্থনীতি গণনা করে।",
  aboutFine: "কোনো API কী নেই। কোনো অ্যানালিটিক্স নেই। ঐচ্ছিক র‍্যাস্টার টাইল সরাসরি নাসা GIBS থেকে আসে। MapLibre GL JS 6.18.0 (BSD-3-Clause) স্থানীয়ভাবে সংযুক্ত। এই সংস্করণে বৈজ্ঞানিক উৎস-পাঠ শুধু ইংরেজিতে; ইন্টারফেসের ভাষা নির্বাচিত দেশ থেকে স্বাধীন।",
};

const DICTS = { en: EN, bn: BN };
let current = "en";

export function setLocale(locale) {
  current = DICTS[locale] ? locale : "en";
  document.documentElement.lang = current;
  return current;
}

export function getLocale() {
  return current;
}

export function t(key, vars) {
  const dict = DICTS[current] || EN;
  let value = dict[key];
  if (value === undefined) value = EN[key];
  if (value === undefined) return key;
  if (vars) {
    for (const [name, replacement] of Object.entries(vars)) {
      value = value.replaceAll(`{${name}}`, String(replacement));
    }
  }
  return value;
}

export function has(key) {
  return Object.prototype.hasOwnProperty.call(DICTS[current] || EN, key);
}

export function isBangla() {
  return current === "bn";
}

/** Localised admin level label for search results and facts. */
export function levelLabel(level, countryCode) {
  if (countryCode === "BD") {
    if (level === 1) return t("levelDivision");
    if (level === 2) return t("levelDistrict");
    if (level === 3) return t("levelUpazila");
  }
  if (countryCode === "US") {
    if (level === 1) return t("levelState");
    if (level === 2) return t("levelCounty");
  }
  if (!level) return t("levelCountry");
  return t("adminUnit");
}

export function readinessLabel(value) {
  switch (value) {
    case "research_pilot":
      return t("modeResearchPilot");
    case "conditional":
      return t("modeConditional");
    case "exploration":
      return t("modeExploration");
    case "validated_with_evidence":
      return t("modeValidated");
    case "available":
      return t("availAvailable");
    case "requires_input":
      return t("availRequiresInput");
    case "blocked":
      return t("availBlocked");
    case "not_scoped":
      return t("availNotScoped");
    default:
      return String(value || "—").replaceAll("_", " ");
  }
}

export function analysisLabel(name) {
  const key = `analysis_${name}`;
  return has(key) ? t(key) : name;
}

/** Apply translations to DOM nodes carrying data-i18n* attributes. */
export function applyStatic(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-html]").forEach((node) => {
    node.innerHTML = t(node.dataset.i18nHtml);
  });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.placeholder = t(node.dataset.i18nPlaceholder);
  });
  root.querySelectorAll("[data-i18n-title]").forEach((node) => {
    node.title = t(node.dataset.i18nTitle);
  });
  root.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.title = t("docTitle");
}

// Analysis labels live outside the main object so readinessLabel can stay tidy.
for (const [locale, dict] of Object.entries(DICTS)) {
  Object.assign(dict, {
    analysis_climate: locale === "bn" ? "জলবায়ু" : "climate",
    analysis_soil: locale === "bn" ? "মাটি" : "soil",
    analysis_water: locale === "bn" ? "পানি" : "water",
    analysis_rotation: locale === "bn" ? "শস্য আবর্তন" : "rotation",
    analysis_economics: locale === "bn" ? "অর্থনীতি" : "economics",
  });
}
