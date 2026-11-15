/** Thin client for the local TerraLens JSON API.
 *  Every route returns the shared envelope: {status, data, insufficiencies, warnings, limitations}.
 *  Errors keep the typed code so the UI can say why something failed instead of guessing. */

export class ApiError extends Error {
  constructor(message, { code = "client_error", payload = null, httpStatus = 0 } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.payload = payload;
    this.httpStatus = httpStatus;
  }
}

const CACHE_TTL_MS = 5 * 60 * 1000;
const cache = new Map();

function cacheKey(path, params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  }
  return `${path}?${query.toString()}`;
}

async function request(path, { params, method = "GET", body, timeout = 20000, cacheable = false } = {}) {
  const key = cacheKey(path, params);
  if (cacheable && cache.has(key)) {
    const hit = cache.get(key);
    if (Date.now() - hit.at < CACHE_TTL_MS) return hit.value;
  }

  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(params || {})) {
    if (value !== undefined && value !== null && value !== "") query.set(name, String(value));
  }
  const url = query.toString() ? `${path}?${query}` : path;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  let response;
  try {
    response = await fetch(url, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });
  } catch (error) {
    clearTimeout(timer);
    const aborted = error && error.name === "AbortError";
    throw new ApiError(
      aborted ? "The local API timed out." : "The local API could not be reached.",
      { code: aborted ? "timeout" : "network_error", payload: null, httpStatus: 0 },
    );
  }
  clearTimeout(timer);

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!payload || typeof payload !== "object") {
    throw new ApiError("The API returned a response that is not JSON.", {
      code: "bad_response",
      payload,
      httpStatus: response.status,
    });
  }

  if (!response.ok || payload.status === "refused") {
    const first = (payload.insufficiencies && payload.insufficiencies[0]) || {};
    throw new ApiError(first.message || `Request failed with HTTP ${response.status}.`, {
      code: first.code || `http_${response.status}`,
      payload,
      httpStatus: response.status,
    });
  }

  if (cacheable) cache.set(key, { at: Date.now(), value: payload });
  return payload;
}

function data(payload) {
  return payload.data;
}

export async function health() {
  return data(await request("/api/terralens/health", { timeout: 6000 }));
}

export async function config() {
  return data(await request("/api/terralens/config", { cacheable: true }));
}

export async function layers(countryCode) {
  return data(await request("/api/terralens/layers", { params: { country: countryCode || "" }, cacheable: true }));
}

export async function sources() {
  return data(await request("/api/terralens/sources", { cacheable: true }));
}

export async function regions() {
  return data(await request("/api/terralens/regions", { cacheable: true }));
}

export async function profile({ lat, lon, region, locale = "en" }) {
  return data(await request("/api/terralens/profile", { params: { lat, lon, region, locale } }));
}

export async function search(query, { country, limit = 12 } = {}) {
  return data(await request("/api/terralens/search", { params: { q: query, country, limit }, timeout: 12000 }));
}

/** POST a drawn polygon or an approximate point. Refusals arrive as typed
 *  insufficiencies inside the selection, so callers can render them. */
export async function field(body) {
  return request("/api/terralens/field", { method: "POST", body, timeout: 20000 });
}

/** Fetch a bundled GeoJSON layer. These are static files, not API envelopes. */
export async function geojson(file) {
  const response = await fetch(`./data/admin/${file}`, { cache: "force-cache" });
  if (!response.ok) {
    throw new ApiError(`Boundary file ${file} did not load.`, {
      code: "boundary_unavailable",
      httpStatus: response.status,
    });
  }
  return response.json();
}

export function clearCache() {
  cache.clear();
}
