/** TerraLens Region Explorer — application shell.
 *
 *  Binds the static UI to the local JSON API, the MapLibre view and the SVG
 *  atlas fallback. Every dynamic statement comes from the router: readiness,
 *  limitations, typed unknowns, footprints and source licences are rendered as
 *  supplied, never recomputed here.
 */

import * as api from "./api.js";
import { createMapView } from "./map.js";
import { createAtlas } from "./fallback.js";
import {
  applyStatic,
  getLocale,
  levelLabel,
  readinessLabel,
  analysisLabel,
  setLocale,
  t,
} from "./i18n.js";

const DEFAULT_POINT = { lat: 23.8103, lon: 90.4125 }; // Dhaka: BD national context
const PILOT_ORDER = ["BD-RAJ-BARIND", "BD-COASTAL", "US-IA-STORY", "GLOBAL"];
const TABS = ["region", "field", "layers", "sources"];
const BOUNDARY_DETAIL = {
  "world-countries": 0,
  "bd-adm1": 1,
  "us-adm1": 1,
  "bd-adm2": 2,
  "us-ia-adm2": 2,
  "bd-adm3": 3,
};
// Natural Earth carries no Bangla country names. These are interface labels,
// not boundary attributes; anything absent falls back to the source name.
const COUNTRY_BN = {
  BD: "বাংলাদেশ",
  US: "মার্কিন যুক্তরাষ্ট্র",
  IN: "ভারত",
  NP: "নেপাল",
  LK: "শ্রীলঙ্কা",
  PK: "পাকিস্তান",
  BT: "ভুটান",
  MM: "মিয়ানমার",
};
const ATLAS_FILES = {
  BD: ["bd_adm1.geojson", "bd_adm2.geojson", "bd_adm3.geojson"],
  US: ["us_adm1.geojson", "us_ia_adm2.geojson"],
};

const state = {
  config: null,
  sources: [],
  layers: [],
  layerCountry: null,
  profile: null,
  lat: DEFAULT_POINT.lat,
  lon: DEFAULT_POINT.lon,
  zoom: null,
  region: null,
  locale: "en",
  layerId: null,
  date: null,
  grids: true,
  pilots: true,
  detail: 0,
  detailOverride: null,
  tab: "region",
  static: false,
  kind: "pending",
  view: null,
  field: null,
  fieldGeometry: null,
  atlas: {
    countries: null,
    adminCountry: null,
    admins: [],
    worldPromise: null,
    adminPromise: null,
  },
  sourceFilter: "",
  search: { items: [], active: -1, seq: 0, timer: 0 },
};

let viewPromise = null;
let profileSeq = 0;
let urlTimer = 0;
let toastTimer = 0;
let searchFailedOnce = false;
let staticToastShown = false;

const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function isBn() {
  return getLocale() === "bn";
}

function localized(record, field = "name", fieldBn = "nameBn") {
  if (!record) return "";
  return isBn() ? record[fieldBn] || record[field] || "" : record[field] || record[fieldBn] || "";
}

function countryName(country) {
  if (!country) return "";
  if (isBn()) return country.nameBn || COUNTRY_BN[country.code] || country.name || "";
  return country.name || "";
}

function regionLabelOf(regionId, fallback = "") {
  const pack = state.config && state.config.regionPacks
    ? state.config.regionPacks.find((candidate) => candidate.regionId === regionId)
    : null;
  if (!pack) return fallback || regionId || "";
  return isBn() ? pack.labelBn || pack.label : pack.label;
}

function shortLabel(text) {
  return String(text || "").split("·")[0].trim();
}

function num(value, digits = 0) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return new Intl.NumberFormat(isBn() ? "bn-BD" : "en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(Number(value));
}

function pct(value) {
  if (value === null || value === undefined) return "—";
  const amount = Number(value) * 100;
  if (!Number.isFinite(amount)) return "—";
  if (amount >= 1) return num(amount, 1);
  if (amount >= 0.01) return num(amount, 2);
  if (amount >= 0.0001) return num(amount, 4);
  return `<${num(0.0001, 4)}`;
}

function formatPoint(lat, lon, digits = 4) {
  const latDir = lat >= 0 ? "N" : "S";
  const lonDir = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(digits)}° ${latDir}, ${Math.abs(lon).toFixed(digits)}° ${lonDir}`;
}

function latestFor(layer) {
  const offset = Number(layer && layer.dateOffsetDays) || 0;
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - offset);
  return date.toISOString().slice(0, 10);
}

function isStaticLayer(layer) {
  if (!layer) return false;
  return layer.id === "srtm-elevation" || /^Static/i.test(layer.temporalResolution || "");
}

function toast(message) {
  const node = $("toast");
  if (!node) return;
  node.textContent = message;
  node.hidden = false;
  requestAnimationFrame(() => node.classList.add("is-visible"));
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    node.classList.remove("is-visible");
    toastTimer = setTimeout(() => {
      node.hidden = true;
      toastTimer = 0;
    }, 220);
  }, 5200);
}

function showNotice(title, body) {
  const notice = $("offline-notice");
  if (!notice) return;
  $("notice-title").textContent = title;
  $("notice-body").textContent = body;
  notice.hidden = false;
}

function hideNotice() {
  const notice = $("offline-notice");
  if (notice) notice.hidden = true;
}

function updateCoords(lon, lat) {
  const node = $("coords");
  if (!node || !Number.isFinite(lon) || !Number.isFinite(lat)) return;
  node.textContent = formatPoint(lat, lon, 4);
}

function showTab(tab, { sync = true } = {}) {
  if (!TABS.includes(tab)) tab = "region";
  state.tab = tab;
  TABS.forEach((name) => {
    const button = $(`tab-${name}`);
    const panel = $(`panel-${name}`);
    if (!button || !panel) return;
    const selected = name === tab;
    button.setAttribute("aria-selected", selected ? "true" : "false");
    button.tabIndex = selected ? 0 : -1;
    panel.hidden = !selected;
  });
  if (sync) syncUrl();
}

function readUrl() {
  const params = new URLSearchParams(window.location.search);
  const number = (name) => {
    if (!params.has(name)) return null;
    const value = Number(params.get(name));
    return Number.isFinite(value) ? value : null;
  };
  let locale = params.get("locale");
  if (locale !== "en" && locale !== "bn") {
    try {
      const stored = window.localStorage.getItem("terralens.locale");
      locale = stored === "bn" ? "bn" : "en";
    } catch {
      locale = "en";
    }
  }
  let tab = params.get("tab");
  if (!TABS.includes(tab)) tab = "region";
  let geometry = null;
  const encodedField = params.get("f");
  if (encodedField) {
    try {
      const candidate = JSON.parse(encodedField);
      if (candidate && (candidate.type === "Polygon" || candidate.type === "MultiPolygon")) {
        geometry = candidate;
      }
    } catch {
      geometry = null;
    }
  }
  const lat = number("lat");
  const lon = number("lon");
  return {
    lat: lat !== null && lat >= -90 && lat <= 90 ? lat : null,
    lon: lon !== null && lon >= -180 && lon <= 180 ? lon : null,
    zoom: number("zoom"),
    locale,
    region: params.get("region") || null,
    layer: params.get("layer") || null,
    date: /^\d{4}-\d{2}-\d{2}$/.test(params.get("date") || "") ? params.get("date") : null,
    grids: params.get("grids") !== "0",
    pilots: params.get("pilots") !== "0",
    detail: params.has("detail") ? Math.max(0, Math.min(3, Number(params.get("detail")) || 0)) : null,
    tab,
    static: params.get("static") === "1",
    geometry,
  };
}

function syncUrl() {
  const params = new URLSearchParams();
  if (Number.isFinite(state.lat)) params.set("lat", state.lat.toFixed(6));
  if (Number.isFinite(state.lon)) params.set("lon", state.lon.toFixed(6));
  if (state.region) params.set("region", state.region);
  if (state.locale !== "en") params.set("locale", state.locale);
  if (state.layerId) {
    params.set("layer", state.layerId);
    if (state.date) params.set("date", state.date);
  }
  if (!state.grids) params.set("grids", "0");
  if (!state.pilots) params.set("pilots", "0");
  if (state.detailOverride !== null) params.set("detail", String(state.detailOverride));
  if (state.tab !== "region") params.set("tab", state.tab);
  if (state.static) params.set("static", "1");
  if (Number.isFinite(state.zoom)) params.set("zoom", state.zoom.toFixed(2));
  if (state.fieldGeometry) {
    try {
      const raw = JSON.stringify(state.fieldGeometry);
      if (raw.length <= 7000) params.set("f", raw);
    } catch {
      /* nothing to persist */
    }
  }
  const query = params.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}

function scheduleUrl() {
  if (urlTimer) return;
  urlTimer = setTimeout(() => {
    urlTimer = 0;
    syncUrl();
  }, 320);
}

// -------------------------------------------------------------------------- view

async function makeView() {
  const mapElement = $("map");
  const fallbackElement = $("map-fallback");

  if (state.static) return makeAtlas({ explicit: true });

  let mapView = null;
  try {
    mapView = await Promise.race([
      createMapView(mapElement, viewHandlers()),
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error("MapLibre did not start in time.")), 12000);
      }),
    ]);
    await Promise.race([
      mapView.ready,
      new Promise((_, reject) => {
        setTimeout(() => reject(new Error("The map style did not load in time.")), 10000);
      }),
    ]);
    state.kind = "map";
    state.static = false;
    state.view = mapView;
    mapView.setBoundaryDetail(state.detail);
    $("map-mode-badge").hidden = true;
    updateStaticUi();
    return mapView;
  } catch (error) {
    console.warn("TerraLens: using the static atlas.", error);
    const disposable = mapView || state.view;
    if (disposable && disposable.destroy) {
      try {
        disposable.destroy();
      } catch {
        /* the failed map may be half-built */
      }
    }
    state.view = null;
    if (mapElement) mapElement.style.display = "none";
    if (fallbackElement) fallbackElement.hidden = false;
    return makeAtlas({ explicit: false });
  }
}

function makeAtlas({ explicit = false } = {}) {
  const mapElement = $("map");
  const fallbackElement = $("map-fallback");
  if (mapElement) mapElement.style.display = "none";
  if (fallbackElement) fallbackElement.hidden = false;

  const atlas = createAtlas(fallbackElement, {
    onPoint: ([lon, lat]) => {
      applyLocation(lat, lon, { sync: true });
    },
    onViewChange: handleViewChange,
  });

  state.kind = "atlas";
  // Only a user-requested static mode belongs in the URL; an automatic
  // fallback should not pin every later visit to the atlas.
  state.static = explicit;
  state.view = atlas;
  $("map-mode-badge").hidden = false;
  $("map-mode-badge").textContent = t("staticBadge");
  updateStaticUi();

  state.atlas.worldPromise = api
    .geojson("world_countries.geojson")
    .then((collection) => {
      state.atlas.countries = collection;
      atlas.setData({ countries: collection });
      return collection;
    })
    .catch(() => {
      showNotice(t("boundaryFailTitle"), t("boundaryFailBody"));
      return null;
    });

  if (!staticToastShown) {
    staticToastShown = true;
    toast(t("toastStatic"));
  }
  return atlas;
}

function initView() {
  if (!viewPromise) viewPromise = makeView();
  return viewPromise;
}

function ensureView() {
  return viewPromise || initView();
}

function viewHandlers() {
  return {
    onPoint: ([lon, lat]) => {
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
      applyLocation(lat, lon, { sync: true });
    },
    onHover: showHover,
    onViewChange: handleViewChange,
    onDrawFinish: (geometry) => submitField({ geometry }),
    onDrawState: setDrawState,
    onDrawTooFew: () => toast(t("toastNeedThree")),
    onTileError: handleTileError,
    onBoundaryError: () => showNotice(t("boundaryFailTitle"), t("boundaryFailBody")),
    onLayerState: () => {},
  };
}

function handleViewChange(view) {
  if (!view || !Array.isArray(view.center)) return;
  if (Number.isFinite(view.zoom)) state.zoom = view.zoom;
  updateCoords(view.center[0], view.center[1]);
  scheduleUrl();
}

function updateStaticUi() {
  const atlasMode = state.kind === "atlas";
  const badge = $("map-mode-badge");
  if (badge) {
    badge.hidden = !atlasMode;
    if (atlasMode) badge.textContent = t("staticBadge");
  }
  const drawButton = $("draw-btn");
  const fieldDraw = $("field-draw");
  [drawButton, fieldDraw].forEach((button) => {
    if (!button) return;
    button.disabled = atlasMode;
    if (atlasMode) {
      button.title = t("fieldStaticDisabled");
      button.setAttribute("aria-label", t("fieldStaticDisabled"));
    } else {
      button.title = t("drawTitle");
      button.setAttribute("aria-label", t("drawTitle"));
    }
  });
  const gridsButton = $("grids-btn");
  if (gridsButton) gridsButton.setAttribute("aria-pressed", state.grids ? "true" : "false");
}

function handleTileError(reason) {
  if (reason === "offline" || !navigator.onLine) {
    showNotice(t("offlineTitleNoNet"), t("offlineBodyNoNet"));
  } else {
    showNotice(t("tileFailTitle"), t("tileFailBody"));
  }
}

function showHover(info) {
  const card = $("hover-card");
  if (!card) return;
  if (!info) {
    card.hidden = true;
    return;
  }
  const countryCode = state.profile ? state.profile.location.countryCode : null;
  const name = isBn() && info.nameBn ? info.nameBn : info.name;
  card.innerHTML = `<b>${esc(name)}</b><span>${esc(levelLabel(info.level, countryCode))}</span>`;
  card.hidden = false;
  const shell = card.parentElement ? card.parentElement.getBoundingClientRect() : null;
  const left = Math.max(8, Math.min(info.x + 14, (shell ? shell.width : 800) - 265));
  const top = Math.max(8, Math.min(info.y + 16, (shell ? shell.height : 600) - 70));
  card.style.left = `${left}px`;
  card.style.top = `${top}px`;
}

// ------------------------------------------------------------------------ profile

async function loadProfile(params, options = {}) {
  const token = ++profileSeq;
  try {
    const profile = await api.profile({
      lat: params.lat,
      lon: params.lon,
      region: params.region || undefined,
      locale: state.locale,
    });
    if (token !== profileSeq) return null;
    state.profile = profile;
    state.lat = profile.location.lat;
    state.lon = profile.location.lon;
    state.region = profile.region.regionId;
    clearRegionError();
    fillCoordInputs();
    renderProfile();
    await ensureLayers(profile.location.countryCode);
    applyLayer({ announce: false });
    await applyProfileToView(profile, options);
    if (options.sync !== false) syncUrl();
    return profile;
  } catch (error) {
    if (token === profileSeq) handleProfileError(error);
    return null;
  }
}

function applyLocation(lat, lon, options = {}) {
  const latitude = Number(lat);
  const longitude = Number(lon);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return Promise.resolve(null);
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    toast("Latitude must be −90..90 and longitude −180..180.");
    return Promise.resolve(null);
  }
  return loadProfile({ lat: latitude, lon: longitude, region: options.region }, options);
}

function applyRegion(regionId, options = {}) {
  return loadProfile({ region: regionId }, options);
}

function handleProfileError(error) {
  const message = (error && error.message) || t("toastProfileFail");
  toast(message);
  if (!state.profile) {
    $("region-name").textContent = t("errorTitle");
    $("region-sub").textContent = t("errorBody");
    $("readiness-badge").dataset.state = "exploration";
    $("readiness-badge").textContent = "—";
    renderRegionError(error);
  }
}

function renderRegionError(error) {
  const host = $("panel-region");
  if (!host) return;
  host.querySelectorAll(".panel-error").forEach((node) => node.remove());
  const head = host.querySelector(".dossier-head");
  if (!head) return;
  const box = document.createElement("div");
  box.className = "panel-error";
  box.innerHTML = `<strong>${esc(t("errorTitle"))}</strong>
    <p>${esc(t("errorBody"))}</p>
    <p>${esc((error && error.message) || "")}</p>
    <button type="button" class="btn btn--ghost btn--tiny" id="retry-boot">${esc(t("retry"))}</button>`;
  head.after(box);
  const retry = box.querySelector("#retry-boot");
  if (retry) {
    retry.addEventListener("click", async () => {
      box.remove();
      await loadReferenceData();
      await applyLocation(state.lat, state.lon, { sync: true });
    });
  }
}

function clearRegionError() {
  const host = $("panel-region");
  if (host) host.querySelectorAll(".panel-error").forEach((node) => node.remove());
}

function fillCoordInputs() {
  const latInput = $("lat-input");
  const lonInput = $("lon-input");
  if (latInput && document.activeElement !== latInput) latInput.value = state.lat.toFixed(4);
  if (lonInput && document.activeElement !== lonInput) lonInput.value = state.lon.toFixed(4);
}

function autoDetail(profile) {
  return Math.min(3, Math.max(0, (profile.admin || []).length));
}

async function applyProfileToView(profile, options = {}) {
  await ensureView();
  const detail = state.detailOverride !== null ? state.detailOverride : autoDetail(profile);
  state.detail = detail;

  if (state.kind === "map" && state.view) {
    state.view.setBoundaryDetail(detail);
    await state.view.setProfile(profile);
    state.view.setGrids(profile.footprints, state.grids);
    if (!state.pilots) state.view.setPilots(null);
    const center = [profile.location.lon, profile.location.lat];
    if (Number.isFinite(options.zoom)) state.view.flyTo(center, options.zoom);
    else if (options.bbox) state.view.fitBBox(options.bbox);
  } else if (state.kind === "atlas" && state.view) {
    state.view.setDetail(detail);
    await applyAtlasProfile(profile, options);
  }
  renderLayers();
}

// ------------------------------------------------------------------------- atlas

async function ensureAtlasAdmins(countryCode) {
  if (!ATLAS_FILES[countryCode]) {
    state.atlas.adminCountry = countryCode || null;
    state.atlas.admins = [];
    return [];
  }
  if (state.atlas.adminCountry === countryCode && state.atlas.admins.length) return state.atlas.admins;
  if (state.atlas.adminPromise && state.atlas.adminCountry === countryCode) return state.atlas.adminPromise;

  state.atlas.adminCountry = countryCode;
  state.atlas.adminPromise = (async () => {
    const collections = await Promise.allSettled(
      ATLAS_FILES[countryCode].map((file) => api.geojson(file)),
    );
    const features = [];
    for (const result of collections) {
      if (result.status !== "fulfilled" || !result.value || !result.value.features) continue;
      for (const feature of result.value.features) {
        const props = feature.properties || {};
        features.push({
          ...feature,
          bbox: props.bbox || null,
          level: props.level || 0,
        });
      }
    }
    if (!features.length) showNotice(t("boundaryFailTitle"), t("boundaryFailBody"));
    state.atlas.admins = features;
    state.atlas.adminPromise = null;
    return features;
  })();
  return state.atlas.adminPromise;
}

function atlasGrids(profile) {
  if (!state.grids || !profile) return [];
  return Object.values(profile.footprints || {});
}

function atlasPilots(profile) {
  if (!state.pilots || !profile) return [];
  const ids = new Set(profile.region.admin2Ids || []);
  if (!ids.size) return [];
  return state.atlas.admins.filter((feature) => ids.has(feature.properties && feature.properties.id));
}

function atlasSelected(profile) {
  if (!profile) return null;
  const deepest = profile.admin && profile.admin.length ? profile.admin[profile.admin.length - 1] : null;
  if (deepest) {
    const match = state.atlas.admins.find((feature) => feature.properties && feature.properties.id === deepest.id);
    if (match) return match;
  }
  if (profile.country && state.atlas.countries) {
    return state.atlas.countries.features.find(
      (feature) => feature.properties && feature.properties.id === profile.country.id,
    ) || null;
  }
  return null;
}

function atlasLabels(profile) {
  const labels = [];
  if (state.atlas.countries && profile.country) {
    labels.push({
      lon: profile.country.representativePoint[0],
      lat: profile.country.representativePoint[1],
      text: countryName(profile.country),
    });
  }
  if (profile.region && profile.region.bbox) {
    const box = profile.region.bbox;
    labels.push({
      lon: (box[0] + box[2]) / 2,
      lat: (box[1] + box[3]) / 2,
      text: shortLabel(isBn() ? profile.region.labelBn : profile.region.label),
    });
  }
  return labels;
}

async function applyAtlasProfile(profile, options = {}) {
  if (state.atlas.worldPromise) await state.atlas.worldPromise;
  await ensureAtlasAdmins(profile.location.countryCode);
  const atlas = state.view;
  if (!atlas) return;

  atlas.setData({
    admins: state.atlas.admins,
    selected: atlasSelected(profile),
    pilots: atlasPilots(profile),
    point: { lon: profile.location.lon, lat: profile.location.lat },
    grids: atlasGrids(profile),
    field: state.fieldGeometry,
    labels: atlasLabels(profile),
    locale: state.locale,
  });

  const center = [profile.location.lon, profile.location.lat];
  if (Number.isFinite(options.zoom)) {
    atlas.flyTo(center, options.zoom);
  } else if (options.bbox) {
    atlas.fitBBox(options.bbox);
  } else if (profile.location.insidePilotExtent && profile.region.bbox) {
    atlas.fitBBox(profile.region.bbox);
  } else {
    const depth = (profile.admin || []).length;
    const zoom = depth >= 3 ? 9 : depth === 2 ? 7.4 : depth === 1 ? 5.6 : profile.location.countryCode ? 4.4 : 2.2;
    atlas.flyTo(center, zoom);
  }
  updateCoords(center[0], center[1]);
}

// ---------------------------------------------------------------------- profile UI

function renderProfile() {
  const profile = state.profile;
  if (!profile) return;
  const country = profile.country;
  const region = profile.region;
  const countryLabel = country ? countryName(country) : "";
  const regionName = isBn() ? region.labelBn || region.label : region.label;
  const chain = (profile.admin || []).map((unit) => localized(unit));
  const placeLine = [countryLabel || t("noAdmin"), ...chain].filter(Boolean).join(" · ");

  $("region-name").textContent = regionName;
  $("region-sub").textContent = placeLine;
  $("readiness-badge").dataset.state = profile.readinessOverall || "exploration";
  $("readiness-badge").textContent = readinessLabel(profile.readinessOverall);

  renderBreadcrumb(profile);
  renderFacts(profile);
  renderFarmer(profile);
  renderGates(profile);
  renderLimitations(profile);
  renderMissing(profile);
  renderWarnings(profile);
  renderUnknowns(profile);
  renderDatasets(profile);
  renderFootprints(profile);

  $("dossier-region-id").textContent = region.regionId;
  $("dossier-title").textContent = regionName;
  const summary = [region.description, region.extentBasis].filter(Boolean).join(" ");
  $("dossier-summary").textContent = summary;

  renderChips(profile);
  renderPilots();
  renderSources();
}

function renderBreadcrumb(profile) {
  const nav = $("admin-chain");
  if (!nav) return;
  nav.replaceChildren();
  const addCrumb = (label, onClick, current = false) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "crumb";
    button.textContent = label;
    if (current) button.setAttribute("aria-current", "true");
    if (onClick) button.addEventListener("click", onClick);
    else button.disabled = true;
    nav.appendChild(button);
  };

  if (profile.country) {
    addCrumb(countryName(profile.country), () => {
      const point = profile.country.representativePoint;
      applyLocation(point[1], point[0], { bbox: profile.country.bbox });
    }, profile.admin.length === 0);
  }
  (profile.admin || []).forEach((unit, index) => {
    const separator = document.createElement("span");
    separator.className = "crumb-sep";
    separator.textContent = "›";
    separator.setAttribute("aria-hidden", "true");
    nav.appendChild(separator);
    addCrumb(localized(unit), () => {
      if (unit.centroid) applyLocation(unit.centroid[1], unit.centroid[0], {});
    }, index === profile.admin.length - 1);
  });
}

function renderFacts(profile) {
  const host = $("fact-grid");
  if (!host) return;
  host.replaceChildren();
  const country = profile.country;
  const rows = [];

  rows.push([
    t("factCountry"),
    country ? `${countryName(country)} (${country.code})` : "—",
  ]);

  if (profile.admin && profile.admin.length) {
    profile.admin.forEach((unit) => {
      rows.push([levelLabel(unit.level, profile.location.countryCode), localized(unit)]);
    });
  } else {
    rows.push([t("adminUnit"), t("noAdmin")]);
  }

  rows.push([t("factMode"), readinessLabel(profile.region.mode)]);
  rows.push([
    t("factPilot"),
    profile.location.insidePilotExtent
      ? `${t("inPilot")} · ${shortLabel(isBn() ? profile.region.labelBn : profile.region.label)}`
      : t("outsidePilot"),
  ]);
  if (Number.isFinite(Number(profile.region.approxAreaKm2))) {
    rows.push([t("factArea"), `${num(profile.region.approxAreaKm2, 0)} ${t("unitsKm2")}`]);
  }
  rows.push([t("factReadiness"), readinessLabel(profile.region.readinessCap)]);
  rows.push([t("factPoint"), `${profile.location.lat.toFixed(4)}, ${profile.location.lon.toFixed(4)}`, true]);
  if (profile.location.nearestAdminKm !== null && profile.location.nearestAdminKm !== undefined
      && Number.isFinite(Number(profile.location.nearestAdminKm))) {
    rows.push([t("factNearest"), t("kmAway", { n: num(profile.location.nearestAdminKm, 1) })]);
  }

  for (const [label, value, mono] of rows) {
    const wrapper = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    if (mono) detail.className = "is-mono";
    wrapper.append(term, detail);
    host.appendChild(wrapper);
  }
}

function renderFarmer(profile) {
  const link = $("farmer-link");
  const note = $("farmer-note");
  if (!link) return;
  const allowed = Boolean(profile.farmerMode && profile.farmerMode.allowed);
  const supportedBarind = profile.region && profile.region.regionId === "BD-RAJ-BARIND";
  link.href = supportedBarind ? "../planner.html?region=BD-RAJ-BARIND&from=terralens#command-center" : "#";
  link.setAttribute("aria-disabled", (allowed && supportedBarind) ? "false" : "true");
  link.onclick = (event) => {
    event.preventDefault();
    if (!allowed || !supportedBarind) {
      toast("Only the Barind research pilot currently supports the crop-water Command Center. Explore this location in TerraLens instead.");
      return;
    }
    handOffToFarmer(link.href);
  };
  if (note) {
    note.textContent = (allowed && supportedBarind)
      ? "Opens the Barind research Command Center; no personal field is measured."
      : (profile.farmerMode && profile.farmerMode.reason) || t("farmerDisabledNote");
  }
}

async function handOffToFarmer(href) {
  window.location.assign(new URL(href, window.location.origin).href);
}

document.querySelector("#orbitill-back")?.addEventListener("click", () => {
  if (history.length > 1) history.back();
  else window.location.assign("../index.html");
});

function renderChips(profile) {
  const host = $("dossier-chips");
  if (!host) return;
  host.replaceChildren();
  const chips = [
    { text: readinessLabel(profile.region.mode), tone: profile.region.mode },
    {
      text: profile.location.insidePilotExtent ? t("inPilot") : t("outsidePilot"),
      tone: "mono",
    },
    { text: t("chipBoundaries"), tone: "mono" },
    { text: t("chipNoFarmClaims"), tone: "warn" },
    { text: t("chipCropRules"), tone: "mono" },
  ];
  for (const chip of chips) {
    const span = document.createElement("span");
    span.className = "chip";
    span.dataset.tone = chip.tone;
    span.textContent = chip.text;
    host.appendChild(span);
  }
}

function renderGates(profile) {
  const host = $("gates");
  if (!host) return;
  host.replaceChildren();
  const entries = Object.values(profile.analyses || {});
  if (!entries.length) {
    host.appendChild(emptyItem());
    return;
  }
  for (const gate of entries) {
    const details = document.createElement("details");
    details.className = "gate";
    const summary = document.createElement("summary");
    const name = document.createElement("span");
    name.className = "gate-name";
    name.textContent = analysisLabel(gate.analysis);
    const status = document.createElement("span");
    status.className = "gate-status";
    status.dataset.availability = gate.status;
    status.textContent = readinessLabel(gate.status);
    const ready = document.createElement("span");
    ready.className = "gate-ready";
    ready.textContent = readinessLabel(gate.readiness);
    summary.append(name, status, ready);

    const body = document.createElement("div");
    body.className = "gate-body";
    if (gate.reasons && gate.reasons.length) {
      const reason = document.createElement("p");
      reason.textContent = gate.reasons.join(" ");
      body.appendChild(reason);
    }
    if (gate.missing && gate.missing.length) {
      const list = document.createElement("ul");
      list.className = "missing-list";
      for (const missing of gate.missing) {
        const item = document.createElement("li");
        item.textContent = missing;
        list.appendChild(item);
      }
      body.appendChild(list);
    }
    const owner = document.createElement("p");
    owner.className = "gate-owner";
    owner.innerHTML = `${esc(t("owner"))} <b>${esc(gate.owner || "—")}</b>`;
    body.appendChild(owner);

    details.append(summary, body);
    host.appendChild(details);
  }
}

function emptyItem(text = "—") {
  const item = document.createElement("li");
  item.className = "empty-note";
  item.textContent = text;
  return item;
}

function renderLimitations(profile) {
  const host = $("limitations");
  if (!host) return;
  host.replaceChildren();
  const items = profile.limitations || [];
  if (!items.length) {
    host.appendChild(emptyItem());
    return;
  }
  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    host.appendChild(item);
  }
}

function renderMissing(profile) {
  const host = $("missing-reqs");
  if (!host) return;
  host.replaceChildren();
  const items = profile.missingRequirements || [];
  if (!items.length) {
    host.appendChild(emptyItem());
    return;
  }
  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    host.appendChild(item);
  }
}

function renderWarnings(profile) {
  const host = $("profile-warnings");
  if (!host) return;
  host.replaceChildren();
  const items = profile.warnings || [];
  host.hidden = items.length === 0;
  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    host.appendChild(item);
  }
}

function renderUnknowns(profile) {
  const host = $("unknowns");
  if (!host) return;
  host.replaceChildren();
  const items = profile.unknowns || [];
  if (!items.length) {
    host.appendChild(emptyItem());
    return;
  }
  for (const unknown of items) {
    const item = document.createElement("li");
    item.className = "unknown-card";
    const head = document.createElement("div");
    head.className = "unknown-head";
    const name = document.createElement("span");
    name.className = "unknown-name";
    name.textContent = unknown.name;
    const badge = document.createElement("span");
    badge.className = "unknown-state";
    badge.textContent = unknown.state;
    head.append(name, badge);
    const reason = document.createElement("p");
    reason.textContent = unknown.reason;
    item.append(head, reason);
    if (unknown.sourceNeeded) {
      const need = document.createElement("p");
      need.className = "unknown-need";
      need.textContent = `${t("sourceNeeded")}: ${unknown.sourceNeeded}`;
      item.appendChild(need);
    }
    host.appendChild(item);
  }
}

function renderDatasets(profile) {
  const host = $("datasets");
  if (!host) return;
  host.replaceChildren();
  for (const dataset of profile.datasets || []) {
    const item = document.createElement("li");
    item.className = "dataset";
    item.innerHTML = `
      <div class="dataset-top">
        <div>
          <div class="dataset-name">${esc(dataset.name)}</div>
          <div class="dataset-provider">${esc(dataset.provider)}</div>
        </div>
        <span class="gate-status" data-availability="${esc(dataset.status)}">${esc(readinessLabel(dataset.status))}</span>
      </div>
      <div class="dataset-meta">
        <span><b>${esc(t("layerNative"))}</b> ${esc(dataset.nativeResolution)}</span>
        ${dataset.footprintKm ? `<span><b>${esc(t("datasetFootprint"))}</b> ${esc(dataset.footprintKm)}</span>` : ""}
        <span><b>${esc(t("layerCadence"))}</b> ${esc(dataset.temporalResolution)}</span>
        <span><b>${esc(t("datasetAccess"))}</b> ${esc(dataset.access)}</span>
      </div>
      <p class="dataset-caveat">${esc(dataset.caveat)}</p>`;
    host.appendChild(item);
  }
  if (!(profile.datasets || []).length) host.appendChild(emptyItem());
}

function renderFootprints(profile) {
  const host = $("footprints");
  if (!host) return;
  host.replaceChildren();
  const cells = Object.values(profile.footprints || {});
  if (!cells.length) {
    host.appendChild(emptyItem());
    return;
  }
  for (const cell of cells) {
    const item = document.createElement("li");
    item.className = "footprint";
    const smallest = Math.min(Number(cell.footprintKmNs), Number(cell.footprintKmEw));
    item.innerHTML = `
      <div class="fp-glyph" data-size="${smallest < 15 ? "small" : "normal"}" aria-hidden="true"></div>
      <div>
        <p class="fp-name">${esc(cell.grid)}</p>
        <p class="fp-dims">${esc(num(cell.footprintKmNs, 1))} × ${esc(num(cell.footprintKmEw, 1))} km · ${esc(cell.centerLat.toFixed(3))}, ${esc(cell.centerLon.toFixed(3))}</p>
        <p class="fp-note">${esc(cell.note)}</p>
      </div>`;
    host.appendChild(item);
  }
}

// ------------------------------------------------------------------------- pilots

function renderPilots() {
  const host = $("pilot-list");
  const template = $("tpl-pilot");
  if (!host || !template) return;
  host.replaceChildren();
  const packs = state.config && state.config.regionPacks ? state.config.regionPacks : [];
  for (const regionId of PILOT_ORDER) {
    const pack = packs.find((candidate) => candidate.regionId === regionId);
    if (!pack) continue;
    const node = template.content.firstElementChild.cloneNode(true);
    node.dataset.region = pack.regionId;
    node.classList.toggle("is-active", state.region === pack.regionId);
    node.title = pack.description || pack.label;
    const label = node.querySelector(".pilot-label");
    const mode = node.querySelector(".pilot-mode");
    const dot = node.querySelector(".pilot-dot");
    if (label) label.textContent = shortLabel(isBn() ? pack.labelBn || pack.label : pack.label);
    if (mode) mode.textContent = readinessLabel(pack.mode);
    if (dot) dot.dataset.mode = pack.mode;
    node.addEventListener("click", () => {
      const anchor = pack.representativePoint;
      if (!anchor || !Number.isFinite(anchor[0]) || !Number.isFinite(anchor[1])) return;
      showTab("region");
      applyLocation(anchor[1], anchor[0], {
        region: pack.regionId,
        bbox: pack.bbox || undefined,
        sync: true,
      });
    });
    host.appendChild(node);
  }
}

// ------------------------------------------------------------------------- layers

async function ensureLayers(countryCode) {
  const country = countryCode === "BD" || countryCode === "US" ? countryCode : null;
  const key = country || "GLOBAL";
  if (state.layerCountry === key) return;
  state.layerCountry = key;
  try {
    const payload = await api.layers(country);
    state.layers = payload.layers || [];
    if (state.layerId && !currentLayer()) {
      // A layer carried in the URL may not exist for this country's bundle.
      state.layerId = null;
      state.date = null;
    }
    renderLayers();
    applyLayer({ announce: false });
  } catch (error) {
    state.layerCountry = null;
    toast(error.message || t("toastProfileFail"));
  }
}

function currentLayer() {
  if (!state.layerId) return null;
  return state.layers.find((layer) => layer.id === state.layerId && layer.kind === "raster") || null;
}

function layerTitle(layer) {
  return isBn() ? layer.titleBn || layer.title : layer.title;
}

function renderLayers() {
  const envHost = $("layer-list");
  const baseHost = $("base-layer-list");
  const overlayHost = $("overlay-list");
  if (!envHost || !baseHost || !overlayHost) return;

  const rasters = state.layers.filter((layer) => layer.kind === "raster");
  const options = [];
  options.push(`
    <label class="layer-option">
      <input type="radio" name="env-layer" value="" ${state.layerId ? "" : "checked"}>
      <div class="layer-body">
        <div class="layer-title">${esc(t("layerNoneTitle"))}</div>
        <div class="layer-meta">${esc(t("layerNoneMeta"))}</div>
      </div>
    </label>`);
  for (const layer of rasters) {
    options.push(`
      <label class="layer-option">
        <input type="radio" name="env-layer" value="${esc(layer.id)}" ${state.layerId === layer.id ? "checked" : ""}>
        <div class="layer-body">
          <div class="layer-title">${esc(layerTitle(layer))}</div>
          <div class="layer-meta">${esc(layer.variable)} · ${esc(layer.nativeResolution)}</div>
        </div>
        <span class="layer-tag" data-mode="${esc(layer.mode)}">${esc(layer.mode === "online" ? t("layerOnline") : t("layerOffline"))}</span>
      </label>`);
  }
  envHost.innerHTML = options.join("");

  const bases = state.layers.filter(
    (layer) => layer.kind === "vector" && layer.group === "boundaries",
  );
  baseHost.innerHTML = bases.map((layer) => {
    const detail = BOUNDARY_DETAIL[layer.id];
    const checked = detail === state.detail;
    return `
      <label class="layer-option">
        <input type="radio" name="base-layer" value="${esc(layer.id)}" ${checked ? "checked" : ""}>
        <div class="layer-body">
          <div class="layer-title">${esc(layerTitle(layer))}</div>
          <div class="layer-meta">${esc(layer.nativeResolution)}</div>
        </div>
      </label>`;
  }).join("");

  overlayHost.innerHTML = `
    <label class="layer-option layer-option--check">
      <input type="checkbox" id="overlay-grids" ${state.grids ? "checked" : ""}>
      <div class="layer-body">
        <div class="layer-title">${esc(t("overlayGrids"))}</div>
        <div class="layer-meta">${esc(t("overlayGridsMeta"))}</div>
      </div>
    </label>
    <label class="layer-option layer-option--check">
      <input type="checkbox" id="overlay-pilots" ${state.pilots ? "checked" : ""}>
      <div class="layer-body">
        <div class="layer-title">${esc(t("overlayPilots"))}</div>
        <div class="layer-meta">${esc(t("overlayPilotsMeta"))}</div>
      </div>
    </label>
    <label class="layer-option layer-option--check">
      <input type="checkbox" id="overlay-point" checked disabled>
      <div class="layer-body">
        <div class="layer-title">${esc(t("overlayPoints"))}</div>
        <div class="layer-meta">${esc(t("overlayPointsMeta"))}</div>
      </div>
    </label>`;

  renderDateRow();
}

function selectLayer(layerId) {
  const layer = layerId ? state.layers.find((candidate) => candidate.id === layerId && candidate.kind === "raster") : null;
  state.layerId = layer ? layer.id : null;
  if (layer) {
    if (!state.date || !/^\d{4}-\d{2}-\d{2}$/.test(state.date)) state.date = latestFor(layer);
    applyLayer({ announce: true });
    if (state.kind === "atlas" && layer.mode === "online") toast(t("toastStaticRaster"));
  } else {
    state.layerId = null;
    state.date = null;
    applyLayer({ announce: false });
  }
  // The radio group already reflects the choice; rebuilding it would steal
  // keyboard focus from the control the user just moved.
  renderLegend();
}

function applyLayer({ announce = false } = {}) {
  const layer = currentLayer();
  if (state.kind === "map" && state.view) {
    if (layer && layer.gibsLayer) state.view.setLayer(layer, state.date || latestFor(layer));
    else state.view.setLayer(null);
  }
  renderDateRow();
  renderLegend();
  if (announce && !layer) toast(t("toastNoLayer"));
  syncUrl();
}

function renderDateRow() {
  const row = $("date-row");
  const input = $("layer-date");
  const latestButton = $("date-latest");
  const note = $("date-note");
  if (!row || !input || !latestButton || !note) return;
  const layer = currentLayer();
  if (!layer) {
    row.hidden = true;
    return;
  }
  row.hidden = false;
  const staticLayer = isStaticLayer(layer);
  input.disabled = staticLayer;
  latestButton.disabled = staticLayer;
  const latestDate = latestFor(layer);
  input.max = latestDate;
  if (!staticLayer && state.date && state.date > latestDate) {
    state.date = latestDate;
    input.value = latestDate;
  } else {
    input.value = state.date || latestDate;
  }
  note.textContent = staticLayer ? t("dateStatic") : t("dateNote");
}

function renderLegend() {
  const mode = $("legend-mode");
  const name = $("legend-name");
  const body = $("legend-body");
  const attribution = $("attribution");
  if (!mode || !name || !body || !attribution) return;

  const layer = currentLayer();
  if (!layer) {
    mode.textContent = t("legendModeBoundaries");
    name.textContent = t("legendDefaultName");
    body.innerHTML = `
      <div class="legend-vector">
        <span class="lv-fill" aria-hidden="true"></span>
        <span class="lv-line" aria-hidden="true"></span>
        <p>${esc(t("boundaryNote"))}</p>
      </div>`;
    attribution.textContent = t("attribution");
    return;
  }

  mode.textContent = layer.mode === "online" ? t("layerOnline") : t("layerOffline");
  name.textContent = layerTitle(layer);
  const stops = (layer.legend && layer.legend.stops) || [];
  const gradient = stops.length
    ? `linear-gradient(90deg, ${stops.map((stop) => stop.color).join(", ")})`
    : "linear-gradient(90deg, #22452f, #c5ec58)";
  const first = stops.length ? stops[0].label : "";
  const last = stops.length ? stops[stops.length - 1].label : "";
  const rows = stops.map((stop) => `
    <li><i style="background:${esc(stop.color)}" aria-hidden="true"></i><span>${esc(stop.label)}</span></li>`).join("");
  body.innerHTML = `
    <div class="legend-unit">
      <span>${esc(t("layerUnits"))} <b>${esc(layer.units || "—")}</b></span>
      <span>${esc(t("layerNative"))} <b>${esc(layer.nativeResolution)}</b></span>
      <span>${esc(t("layerCadence"))} <b>${esc(layer.temporalResolution)}</b></span>
    </div>
    <div class="legend-bar" style="background:${gradient}" role="img" aria-label="${esc(layer.title)} colour scale"></div>
    <div class="legend-ticks"><span>${esc(first)}</span><span>${esc(last)}</span></div>
    ${rows ? `<ul class="legend-rows">${rows}</ul>` : ""}
    <p class="legend-note">${esc([layer.legend ? layer.legend.note : "", layer.legend && layer.legend.scaleNote ? layer.legend.scaleNote : "", layer.caveat].filter(Boolean).join(" "))}</p>`;
  attribution.textContent = `${layer.attribution} · ${t("attribution")}`;
}

// ------------------------------------------------------------------------- sources

function renderSources() {
  const host = $("sources-list");
  if (!host) return;
  host.replaceChildren();
  const input = $("source-filter");
  const filter = ((input && input.value) || state.sourceFilter || "").trim().toLowerCase();
  const used = new Set(((state.profile && state.profile.sources) || []).map((source) => source.id));
  let shown = 0;
  for (const source of state.sources) {
    const haystack = [
      source.id, source.title, source.provider, source.usedFor, source.license, source.version,
    ].join(" ").toLowerCase();
    if (filter && !haystack.includes(filter)) continue;
    shown += 1;
    const retrieved = source.retrievedAtUtc ? source.retrievedAtUtc.slice(0, 10) : "—";
    const item = document.createElement("li");
    item.className = "source";
    item.innerHTML = `
      <div class="source-top">
        <div>
          <div class="source-title">${esc(source.title)}</div>
          <span class="source-id">${esc(source.id)}</span>
        </div>
        ${used.has(source.id) ? `<span class="gate-status" data-availability="available">${esc(t("sourceUsedHere"))}</span>` : ""}
      </div>
      <p class="source-provider">${esc(source.provider)}</p>
      <p class="source-used"><b>${esc(t("sourceUsed"))}:</b> ${esc(source.usedFor)}</p>
      <div class="source-foot">
        <a class="source-license" href="${esc(source.licenseUrl)}" target="_blank" rel="noopener noreferrer">${esc(source.license)}</a>
        <span>${esc(source.version)}</span>
        <span>${esc(t("sourceRetrieved", { date: retrieved }))}</span>
        ${source.sha256 ? `<code title="${esc(source.sha256)}">SHA-256 ${esc(source.sha256.slice(0, 16))}…</code>` : ""}
      </div>`;
    host.appendChild(item);
  }
  if (!shown) host.appendChild(emptyItem(t("noSources")));
}

// --------------------------------------------------------------------------- field

function submitField(body) {
  return postField(body, { quiet: false });
}

async function postField(body, { quiet = false } = {}) {
  const payload = {
    ...body,
    region: state.region || undefined,
    locale: state.locale,
  };
  try {
    const envelope = await api.field(payload);
    acceptField(envelope.data, { focus: !quiet });
    if (!quiet) {
      toast(envelope.data && envelope.data.precision === "field_polygon"
        ? t("toastFieldReady")
        : t("toastPoint"));
    }
    return envelope.data;
  } catch (error) {
    if (error && error.payload && error.payload.data) {
      acceptField(error.payload.data, { focus: !quiet });
      if (!quiet) toast(t("toastFieldRefused"));
      return error.payload.data;
    }
    toast((error && error.message) || t("toastFieldRefused"));
    return null;
  }
}

function acceptField(selection, { focus = true } = {}) {
  if (!selection) return;
  state.field = selection;
  const drawable = selection.status === "ok" && selection.precision === "field_polygon" && selection.geometry;
  state.fieldGeometry = drawable ? selection.geometry : null;
  if (state.kind === "map" && state.view) {
    state.view.setField(drawable ? selection.geometry : null);
  } else if (state.kind === "atlas" && state.view) {
    state.view.setData({ field: drawable ? selection.geometry : null });
  }
  renderField();
  if (focus) showTab("field");
  syncUrl();
}

function clearField() {
  state.field = null;
  state.fieldGeometry = null;
  if (state.kind === "map" && state.view) state.view.setField(null);
  else if (state.kind === "atlas" && state.view) state.view.setData({ field: null });
  renderField();
  syncUrl();
}

function regionNameForSelection(selection) {
  return regionLabelOf(selection.regionId, selection.regionLabel);
}

function renderField() {
  const host = $("field-result");
  if (!host) return;
  const selection = state.field;
  if (!selection) {
    host.innerHTML = `
      <div class="field-empty">
        <strong>${esc(t("fieldEmptyTitle"))}</strong>
        <p>${esc(t("fieldEmptyBody"))}</p>
        ${state.kind === "atlas" ? `<p class="fineprint">${esc(t("fieldStaticDisabled"))}</p>` : ""}
      </div>`;
    return;
  }

  const polygon = selection.precision === "field_polygon";
  const area = polygon && selection.areaHectares !== null ? selection.areaHectares : null;
  const acres = polygon && selection.areaAcres !== null ? selection.areaAcres : null;
  const perimeter = polygon && selection.perimeterKm !== null ? selection.perimeterKm : null;
  const parts = [];
  parts.push(`<dl class="field-stats">
    <div><dt>${esc(t("fieldArea"))}</dt><dd>${area === null ? "—" : esc(num(area, area >= 100 ? 1 : area >= 1 ? 2 : 4))}<small>${area === null ? "" : esc(t("fieldHectares"))}</small>${acres === null ? "" : `<small>${esc(num(acres, 0))} ${esc(t("fieldAcres"))}</small>`}</dd></div>
    <div><dt>${esc(t("fieldPerimeter"))}</dt><dd>${perimeter === null ? "—" : esc(num(perimeter, 2))}<small>${perimeter === null ? "" : "km"}</small></dd></div>
    <div><dt>${esc(t("fieldPrecision"))}</dt><dd class="is-text">${esc(polygon ? t("fieldPolygon") : t("fieldPointApprox"))}</dd></div>
    <div><dt>${esc(t("fieldRegion"))}</dt><dd class="is-text">${esc(regionNameForSelection(selection))}</dd></div>
  </dl>`);

  const insufficiencies = selection.insufficiencies || [];
  if (insufficiencies.length) {
    parts.push(`<ul class="field-refusals">${insufficiencies.map((entry) => `
      <li data-code="${esc(entry.code)}"><strong>${esc(entry.code)}</strong>${esc(entry.message)}${entry.remedy ? `<em>${esc(entry.remedy)}</em>` : ""}</li>`).join("")}</ul>`);
  }

  const warnings = selection.warnings || [];
  if (warnings.length) {
    parts.push(`<ul class="field-warnings">${warnings.map((text) => `<li>${esc(text)}</li>`).join("")}</ul>`);
  }

  if (polygon && (selection.footprints || []).length) {
    const blocks = selection.footprints.map((comparison) => {
      const share = comparison.fieldShareOfCell;
      const dotSize = share === null || share === undefined
        ? 5
        : Math.max(2, Math.min(38, Math.round(42 * Math.sqrt(Math.max(0, share)))));
      let shareText;
      if (share === null || share === undefined) {
        const match = String(comparison.fieldSpans || "").match(/([\d,]+)/);
        shareText = match ? t("fieldPixels", { n: match[1] }) : comparison.fieldSpans;
      } else {
        shareText = t("fieldShare", { pct: pct(share) });
      }
      return `<div class="field-fp">
        <div class="fp-cell" aria-hidden="true"><span class="field-dot" style="width:${dotSize}px;height:${dotSize}px"></span></div>
        <div>
          <div class="field-fp-name">${esc(comparison.label)}</div>
          <div class="field-fp-note">${esc(comparison.nativeResolution)} · ${esc(comparison.note)}</div>
        </div>
        <div class="field-fp-share">${esc(shareText)}</div>
      </div>`;
    }).join("");
    parts.push(`<h3>${esc(t("fieldFootprintTitle"))}</h3>
      <p class="dossier-note">${esc(t("fieldFootprintNote"))}</p>
      <div class="field-footprints">${blocks}</div>`);
  } else if (!polygon) {
    parts.push(`<p class="dossier-note">${esc(t("fieldNoFootprints"))} ${esc(t("fieldPointNote"))}</p>`);
  }

  host.innerHTML = parts.join("");
}

// -------------------------------------------------------------------------- search

function hideSearch() {
  const list = $("search-results");
  const input = $("search-input");
  if (list) {
    list.hidden = true;
    list.replaceChildren();
  }
  if (input) input.setAttribute("aria-expanded", "false");
  state.search.items = [];
  state.search.active = -1;
}

function searchMessage(text) {
  const list = $("search-results");
  const input = $("search-input");
  if (!list) return;
  list.innerHTML = `<li class="sr-empty">${esc(text)}</li>`;
  list.hidden = false;
  if (input) input.setAttribute("aria-expanded", "true");
  state.search.items = [];
  state.search.active = -1;
}

async function runSearch(query) {
  const text = query.trim();
  if (text.length < 2) {
    if (text.length === 1) searchMessage(t("searchHint"));
    else hideSearch();
    return;
  }
  const seq = ++state.search.seq;
  searchMessage(t("searching"));
  try {
    const payload = await api.search(text);
    if (seq !== state.search.seq) return;
    state.search.items = payload.results || [];
    renderSearchResults();
  } catch (error) {
    if (seq !== state.search.seq) return;
    searchMessage(t("searchOffline"));
    if (!searchFailedOnce) {
      searchFailedOnce = true;
      toast(t("toastSearchFail"));
    }
  }
}

function renderSearchResults() {
  const list = $("search-results");
  const input = $("search-input");
  if (!list) return;
  const items = state.search.items;
  if (!items.length) {
    searchMessage(t("searchEmpty"));
    return;
  }
  list.innerHTML = items.map((result, index) => {
    const primary = isBn() && result.nameBn ? result.nameBn : result.name;
    const secondary = isBn()
      ? (result.name && result.name !== primary ? result.name : "")
      : (result.nameBn && result.nameBn !== primary ? result.nameBn : "");
    return `<li role="option" data-index="${index}" aria-selected="false" id="search-option-${index}">
      <span class="sr-name">${esc(primary)}${secondary ? `<small>${esc(secondary)}</small>` : ""}</span>
      <span class="sr-kind">${esc(levelLabel(result.level, result.countryCode))}</span>
    </li>`;
  }).join("");
  list.hidden = false;
  if (input) input.setAttribute("aria-expanded", "true");
  state.search.active = -1;
}

function moveSearchActive(delta) {
  if (!state.search.items.length) return;
  const length = state.search.items.length;
  state.search.active = (state.search.active + delta + length) % length;
  const list = $("search-results");
  if (!list) return;
  list.querySelectorAll("li[data-index]").forEach((node) => {
    const selected = Number(node.dataset.index) === state.search.active;
    node.setAttribute("aria-selected", selected ? "true" : "false");
    if (selected) node.scrollIntoView({ block: "nearest" });
  });
}

function selectSearchResult(index) {
  const result = state.search.items[index];
  if (!result) return;
  const input = $("search-input");
  if (input) {
    input.value = isBn() && result.nameBn ? result.nameBn : result.name;
    input.setAttribute("aria-expanded", "false");
  }
  hideSearch();
  showTab("region");
  applyLocation(result.centroid[1], result.centroid[0], {
    region: result.regionId || undefined,
    bbox: result.bbox || undefined,
    sync: true,
  });
}

function parseCoordinateText(text) {
  const match = String(text || "").trim().match(/^(-?\d{1,3}(?:\.\d+)?)\s*[, ]\s*(-?\d{1,3}(?:\.\d+)?)$/);
  if (!match) return null;
  const lat = Number(match[1]);
  const lon = Number(match[2]);
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return { lat, lon };
}

// ------------------------------------------------------------------------- chrome

function bindChrome() {
  document.querySelectorAll("[data-locale]").forEach((button) => {
    button.addEventListener("click", () => {
      const locale = button.dataset.locale === "bn" ? "bn" : "en";
      if (locale === state.locale) return;
      applyUiLocale(locale, { announce: true });
      syncUrl();
    });
  });

  const about = $("about-btn");
  const dialog = $("about-dialog");
  if (about && dialog) {
    about.addEventListener("click", () => {
      if (typeof dialog.showModal === "function") {
        if (!dialog.open) dialog.showModal();
      } else {
        dialog.setAttribute("open", "");
      }
    });
  }

  const searchForm = $("search-form");
  const searchInput = $("search-input");
  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (state.search.active >= 0) {
        selectSearchResult(state.search.active);
        return;
      }
      const coordinate = parseCoordinateText(searchInput.value);
      if (coordinate) {
        hideSearch();
        showTab("region");
        applyLocation(coordinate.lat, coordinate.lon, { sync: true });
        return;
      }
      await runSearch(searchInput.value);
      if (state.search.items.length === 1) selectSearchResult(0);
    });

    searchInput.addEventListener("input", () => {
      const value = searchInput.value;
      if (state.search.timer) clearTimeout(state.search.timer);
      if (value.trim().length < 2) {
        if (value.trim().length === 1) searchMessage(t("searchHint"));
        else hideSearch();
        return;
      }
      state.search.timer = setTimeout(() => {
        state.search.timer = 0;
        runSearch(value);
      }, 260);
    });

    searchInput.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if ($("search-results").hidden) {
          runSearch(searchInput.value);
        } else {
          moveSearchActive(1);
        }
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        moveSearchActive(-1);
      } else if (event.key === "Escape") {
        hideSearch();
      }
    });

    searchInput.addEventListener("focus", () => {
      if (state.search.items.length) {
        $("search-results").hidden = false;
        searchInput.setAttribute("aria-expanded", "true");
      }
    });
  }

  const results = $("search-results");
  if (results) {
    results.addEventListener("mousedown", (event) => {
      if (event.target.closest("li[data-index]")) event.preventDefault();
    });
    results.addEventListener("click", (event) => {
      const item = event.target.closest("li[data-index]");
      if (!item) return;
      selectSearchResult(Number(item.dataset.index));
    });
  }

  const gotoForm = $("goto-form");
  if (gotoForm) {
    gotoForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const lat = Number($("lat-input").value);
      const lon = Number($("lon-input").value);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
        toast("Latitude must be −90..90 and longitude −180..180.");
        return;
      }
      showTab("region");
      applyLocation(lat, lon, { sync: true });
    });
  }

  const centreButton = $("centre-btn");
  if (centreButton) {
    centreButton.addEventListener("click", () => {
      const view = state.view;
      if (!view) return;
      const point = view.getCenter ? view.getCenter() : view.getView().center;
      $("lat-input").value = point[1].toFixed(4);
      $("lon-input").value = point[0].toFixed(4);
      showTab("region");
      applyLocation(point[1], point[0], { sync: true });
    });
  }

  document.querySelectorAll(".tabbar button[data-tab]").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
    button.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const index = TABS.indexOf(button.dataset.tab);
      const next = TABS[(index + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length];
      showTab(next);
      const target = $(`tab-${next}`);
      if (target) target.focus();
    });
  });

  $("zoom-in").addEventListener("click", () => {
    if (state.view && state.view.zoomIn) state.view.zoomIn();
  });
  $("zoom-out").addEventListener("click", () => {
    if (state.view && state.view.zoomOut) state.view.zoomOut();
  });

  $("grids-btn").addEventListener("click", () => toggleGrids());
  $("draw-btn").addEventListener("click", () => {
    if (state.kind !== "map" || !state.view) {
      toast(t("fieldStaticDisabled"));
      return;
    }
    if (state.view.isDrawing()) state.view.finishDraw();
    else {
      showTab("field");
      state.view.startDraw();
    }
  });
  $("field-draw").addEventListener("click", () => {
    if (state.kind !== "map" || !state.view) {
      toast(t("fieldStaticDisabled"));
      return;
    }
    state.view.startDraw();
  });
  $("field-point").addEventListener("click", () => {
    postField({ lat: state.lat, lon: state.lon });
  });
  $("field-clear").addEventListener("click", clearField);
  $("draw-finish").addEventListener("click", () => {
    if (state.view && state.view.isDrawing()) state.view.finishDraw();
  });
  $("draw-cancel").addEventListener("click", () => {
    if (state.view && state.view.cancelDraw) state.view.cancelDraw();
  });

  $("layer-date").addEventListener("change", () => {
    const value = $("layer-date").value;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return;
    state.date = value;
    applyLayer({ announce: false });
    toast(t("toastDate"));
  });
  $("date-latest").addEventListener("click", () => {
    const layer = currentLayer();
    if (!layer) return;
    state.date = latestFor(layer);
    applyLayer({ announce: false });
    toast(t("toastDate"));
  });

  $("layer-list").addEventListener("change", (event) => {
    if (event.target.name !== "env-layer") return;
    selectLayer(event.target.value);
  });
  $("base-layer-list").addEventListener("change", (event) => {
    if (event.target.name !== "base-layer") return;
    const detail = BOUNDARY_DETAIL[event.target.value];
    if (!Number.isFinite(detail)) return;
    state.detailOverride = detail;
    state.detail = detail;
    if (state.kind === "map" && state.view) state.view.setBoundaryDetail(detail);
    else if (state.kind === "atlas" && state.view) state.view.setDetail(detail);
    syncUrl();
  });
  $("overlay-list").addEventListener("change", (event) => {
    if (event.target.id === "overlay-grids") toggleGrids(event.target.checked);
    if (event.target.id === "overlay-pilots") togglePilots(event.target.checked);
  });

  const sourceFilter = $("source-filter");
  if (sourceFilter) {
    sourceFilter.addEventListener("input", () => {
      state.sourceFilter = sourceFilter.value;
      renderSources();
    });
  }

  $("notice-close").addEventListener("click", hideNotice);

  document.addEventListener("keydown", (event) => {
    if (!state.view || !state.view.isDrawing || !state.view.isDrawing()) return;
    if (event.key === "Enter") {
      event.preventDefault();
      state.view.finishDraw();
    } else if (event.key === "Escape") {
      event.preventDefault();
      state.view.cancelDraw();
      toast(t("toastDrawOff"));
    }
  });

  window.addEventListener("offline", () => {
    showNotice(t("offlineTitleNoNet"), t("offlineBodyNoNet"));
  });

  window.addEventListener("online", () => {
    if (!state.layerId) hideNotice();
  });
}

function setDrawState(active) {
  const hint = $("draw-hint");
  const button = $("draw-btn");
  if (hint) hint.hidden = !active;
  if (button) button.setAttribute("aria-pressed", active ? "true" : "false");
  if (active) {
    showTab("field", { sync: false });
    toast(t("toastDrawOn"));
  }
}

function toggleGrids(explicit) {
  state.grids = typeof explicit === "boolean" ? explicit : !state.grids;
  const button = $("grids-btn");
  if (button) button.setAttribute("aria-pressed", state.grids ? "true" : "false");
  const checkbox = $("overlay-grids");
  if (checkbox) checkbox.checked = state.grids;
  if (state.profile) {
    if (state.kind === "map" && state.view) state.view.setGrids(state.profile.footprints, state.grids);
    else if (state.kind === "atlas" && state.view) state.view.setData({ grids: atlasGrids(state.profile) });
  }
  toast(state.grids ? t("toastGridsOn") : t("toastGridsOff"));
  syncUrl();
}

function togglePilots(explicit) {
  state.pilots = typeof explicit === "boolean" ? explicit : !state.pilots;
  const checkbox = $("overlay-pilots");
  if (checkbox) checkbox.checked = state.pilots;
  if (state.profile) {
    if (state.kind === "map" && state.view) {
      state.view.setPilots(state.pilots ? state.profile.region : null);
    } else if (state.kind === "atlas" && state.view) {
      state.view.setData({ pilots: atlasPilots(state.profile) });
    }
  }
  syncUrl();
}

// ------------------------------------------------------------------------ locale

function applyUiLocale(locale, { announce = false } = {}) {
  state.locale = setLocale(locale);
  try {
    window.localStorage.setItem("terralens.locale", state.locale);
  } catch {
    /* storage can be disabled */
  }
  document.querySelectorAll("[data-locale]").forEach((button) => {
    const active = button.dataset.locale === state.locale;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
  applyStatic(document);
  renderPilots();
  renderLayers();
  renderLegend();
  renderSources();
  renderProfile();
  renderField();
  renderDateRow();
  updateStaticUi();
  if (state.kind === "map" && state.view && state.profile && state.pilots) {
    // Boundary labels are DOM markers built by the map module; rebuild them so
    // the pilot label follows the interface language.
    state.view.setPilots(state.profile.region);
  }
  if (announce) toast(t("toastLocale"));
}

// --------------------------------------------------------------------------- boot

async function loadReferenceData() {
  const [configResult, sourceResult] = await Promise.allSettled([api.config(), api.sources()]);
  if (configResult.status === "fulfilled") {
    state.config = configResult.value;
    const version = $("data-version");
    if (version) version.textContent = state.config.dataVersion || "—";
    const pill = $("data-pill");
    if (pill) pill.title = `Boundary bundle ${state.config.dataVersion || ""}`;
  }
  if (sourceResult.status === "fulfilled") {
    state.sources = sourceResult.value.sources || [];
    renderSources();
  }
  renderPilots();
}

async function init() {
  const url = readUrl();
  state.static = url.static;
  state.lat = url.lat !== null ? url.lat : DEFAULT_POINT.lat;
  state.lon = url.lon !== null ? url.lon : DEFAULT_POINT.lon;
  state.zoom = url.zoom;
  state.layerId = url.layer;
  state.date = url.date;
  state.grids = url.grids;
  state.pilots = url.pilots;
  state.detailOverride = url.detail;
  state.region = url.region;
  state.sourceFilter = "";

  bindChrome();
  applyUiLocale(url.locale, { announce: false });
  showTab(url.tab, { sync: false });
  fillCoordInputs();
  updateCoords(state.lon, state.lat);
  initView();

  await loadReferenceData();

  let profile = null;
  if (url.lat !== null && url.lon !== null) {
    profile = await loadProfile(
      { lat: url.lat, lon: url.lon, region: url.region || undefined },
      { zoom: url.zoom, sync: false },
    );
  } else if (url.region) {
    profile = await applyRegion(url.region, { zoom: url.zoom, sync: false });
  } else {
    profile = await applyLocation(DEFAULT_POINT.lat, DEFAULT_POINT.lon, { sync: false });
  }

  if (!profile) {
    await ensureLayers("BD");
    applyLayer({ announce: false });
  }

  if (url.geometry) {
    await postField({ geometry: url.geometry }, { quiet: true });
  }

  syncUrl();
  updateStaticUi();
}

init().catch((error) => {
  console.error("TerraLens boot failed", error);
  toast(t("toastProfileFail"));
});
