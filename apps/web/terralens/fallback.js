/** Honest static atlas fallback.
 *
 *  Used when WebGL or MapLibre cannot start (or with ?static=1). It draws the
 *  same bundled boundaries, pilot extents, native-grid footprints and field
 *  polygon as the vector map, with pan, zoom, and click-to-select. No raster
 *  tiles are implied: the badge says "static atlas" and the legend still states
 *  each layer's native resolution.
 */

const SVG_NS = "http://www.w3.org/2000/svg";
const TILE = 256;
const MIN_ZOOM = 1.6;
const MAX_ZOOM = 12;
const MAX_LAT = 85.05112878;

const clamp = (value, low, high) => Math.min(high, Math.max(low, value));

function mercatorY(lat) {
  const phi = clamp(lat, -MAX_LAT, MAX_LAT) * (Math.PI / 180);
  return 0.5 - Math.log((1 + Math.sin(phi)) / (1 - Math.sin(phi))) / (4 * Math.PI);
}

function inverseMercatorY(merc) {
  const lat = (Math.atan(Math.sinh(Math.PI * (1 - 2 * merc))) * 180) / Math.PI;
  return lat;
}

function ringPath(ring, project) {
  let d = "";
  for (let i = 0; i < ring.length; i += 1) {
    const position = ring[i];
    if (!Array.isArray(position) || position.length < 2) continue;
    const [x, y] = project(position[0], position[1]);
    d += `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }
  return d ? `${d}Z` : "";
}

function geometryPath(geometry, project) {
  if (!geometry) return "";
  const polygons =
    geometry.type === "Polygon"
      ? [geometry.coordinates]
      : geometry.type === "MultiPolygon"
        ? geometry.coordinates
        : [];
  let d = "";
  for (const polygon of polygons) {
    for (const ring of polygon) {
      if (ring && ring.length >= 4) d += ringPath(ring, project);
    }
  }
  return d;
}

const bboxCache = new WeakMap();

function featureBBox(feature) {
  if (bboxCache.has(feature)) return bboxCache.get(feature);
  let west = 180;
  let south = 90;
  let east = -180;
  let north = -90;
  const bump = (position) => {
    if (!Array.isArray(position) || position.length < 2) return;
    const lon = Number(position[0]);
    const lat = Number(position[1]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
    if (lon < west) west = lon;
    if (lon > east) east = lon;
    if (lat < south) south = lat;
    if (lat > north) north = lat;
  };
  const walk = (coords) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number") {
      bump(coords);
      return;
    }
    coords.forEach(walk);
  };
  walk(feature.geometry && feature.geometry.coordinates);
  const box = [west, south, east, north];
  bboxCache.set(feature, box);
  return box;
}

function el(name, attrs) {
  const node = document.createElementNS(SVG_NS, name);
  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      if (value !== undefined && value !== null) node.setAttribute(key, String(value));
    }
  }
  return node;
}

export function createAtlas(container, { onPoint, onViewChange } = {}) {
  container.hidden = false;
  container.innerHTML = "";

  const style = document.createElement("style");
  style.textContent = `
    .tl-atlas { font-family: "Manrope", system-ui, sans-serif; }
    .tl-atlas .country-fill { fill: #16352a; stroke: #4a6a55; stroke-width: .7; }
    .tl-atlas .admin-line { fill: none; stroke: #9db79a; stroke-width: .8; opacity: .75; }
    .tl-atlas .admin-line.lvl3 { stroke: #c5ec58; stroke-width: .5; opacity: .4; }
    .tl-atlas .pilot-fill { fill: rgba(197, 236, 88, .08); stroke: #c5ec58; stroke-width: 1.4; stroke-dasharray: 5 4; }
    .tl-atlas .selected-fill { fill: rgba(197, 236, 88, .22); stroke: #c5ec58; stroke-width: 2; }
    .tl-atlas .grid-line { fill: rgba(245, 243, 235, .1); stroke: #f5f3eb; stroke-width: 1; stroke-dasharray: 3 3; opacity: .85; }
    .tl-atlas .field-fill { fill: rgba(167, 107, 71, .3); stroke: #e29b6d; stroke-width: 2; }
    .tl-atlas .point-ring { fill: none; stroke: #c5ec58; stroke-width: 1.4; }
    .tl-atlas .point-dot { fill: #c5ec58; stroke: #10271e; stroke-width: 1.5; }
    .tl-atlas .atlas-label { fill: #c5ec58; font-size: 9px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; paint-order: stroke; stroke: rgba(6,18,13,.9); stroke-width: 2.4px; }
    .tl-atlas .atlas-note { fill: rgba(217,228,209,.6); font-size: 9.5px; paint-order: stroke; stroke: rgba(6,18,13,.9); stroke-width: 2.6px; }
    .tl-atlas .graticule { stroke: rgba(217,228,209,.08); stroke-width: 1; fill: none; }
  `;
  container.appendChild(style);

  const svg = el("svg", {
    viewBox: "0 0 800 600",
    preserveAspectRatio: "none",
    role: "img",
    "aria-label": "Static boundary atlas. Pan by dragging, zoom with the buttons or mouse wheel, click to select a point.",
  });
  container.appendChild(svg);

  const groups = {};
  for (const name of ["graticule", "countries", "pilots", "admin", "selected", "grids", "field", "points", "labels"]) {
    groups[name] = el("g", { class: `g-${name}` });
    svg.appendChild(groups[name]);
  }

  let width = 800;
  let height = 600;
  const view = { centerLon: 90.35, centerLat: 23.8, zoom: 6 };
  let state = {
    countries: null,
    admins: [],
    pilots: [],
    selected: null,
    point: null,
    field: null,
    grids: [],
    labels: [],
    detail: 3,
    locale: "en",
  };

  let drag = null;
  let timer = 0;

  function size() {
    const rect = container.getBoundingClientRect();
    width = Math.max(320, Math.round(rect.width));
    height = Math.max(240, Math.round(rect.height));
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }

  function worldSize() {
    return TILE * 2 ** view.zoom;
  }

  function project(lon, lat) {
    const scale = worldSize();
    const cx = ((view.centerLon + 180) / 360) * scale;
    const cy = mercatorY(view.centerLat) * scale;
    const x = ((lon + 180) / 360) * scale - cx + width / 2;
    const y = mercatorY(lat) * scale - cy + height / 2;
    return [x, y];
  }

  function unproject(x, y) {
    const scale = worldSize();
    const cx = ((view.centerLon + 180) / 360) * scale + (x - width / 2);
    const cy = mercatorY(view.centerLat) * scale + (y - height / 2);
    const lon = (cx / scale) * 360 - 180;
    const lat = inverseMercatorY(cy / scale);
    return [lon, lat];
  }

  function visibleBox() {
    const scale = worldSize();
    const halfLon = ((width / 2) / scale) * 360;
    const halfMerc = (height / 2) / scale;
    const centerMerc = mercatorY(view.centerLat);
    return {
      west: view.centerLon - halfLon,
      east: view.centerLon + halfLon,
      north: inverseMercatorY(clamp(centerMerc - halfMerc, 0, 1)),
      south: inverseMercatorY(clamp(centerMerc + halfMerc, 0, 1)),
    };
  }

  function markViewChanged() {
    if (onViewChange) onViewChange({ center: [view.centerLon, view.centerLat], zoom: view.zoom });
  }

  function render() {
    size();
    const box = visibleBox();

    // graticule -----------------------------------------------------------
    groups.graticule.replaceChildren();
    for (let lon = -180; lon <= 180; lon += 20) {
      const [x] = project(lon, 0);
      if (x < -4 || x > width + 4) continue;
      groups.graticule.appendChild(el("line", { x1: x, y1: 0, x2: x, y2: height, class: "graticule" }));
    }
    for (let lat = -80; lat <= 80; lat += 20) {
      const [, y] = project(0, lat);
      if (y < -4 || y > height + 4) continue;
      groups.graticule.appendChild(el("line", { x1: 0, y1: y, x2: width, y2: y, class: "graticule" }));
    }

    // countries -----------------------------------------------------------
    groups.countries.replaceChildren();
    if (state.countries && state.countries.features) {
      for (const feature of state.countries.features) {
        const [w, s, e, n] = featureBBox(feature);
        if (e < box.west || w > box.east || n < box.south || s > box.north) continue;
        const d = geometryPath(feature.geometry, project);
        if (d) groups.countries.appendChild(el("path", { d, class: "country-fill", "fill-rule": "evenodd" }));
      }
    }

    // pilots --------------------------------------------------------------
    groups.pilots.replaceChildren();
    for (const pilot of state.pilots) {
      const d = geometryPath(pilot.geometry, project);
      if (d) groups.pilots.appendChild(el("path", { d, class: "pilot-fill", "fill-rule": "evenodd" }));
    }

    // administrative lines -------------------------------------------------
    groups.admin.replaceChildren();
    for (const entry of state.admins) {
      const level = Number(entry.level) || 0;
      if (level > state.detail) continue;
      // Upazila lines are noise at country scale, exactly as on the vector map.
      if (level >= 3 && view.zoom < 7.1) continue;
      const [w, s, e, n] = entry.bbox || featureBBox(entry);
      if (e < box.west || w > box.east || n < box.south || s > box.north) continue;
      const d = geometryPath(entry.geometry, project);
      if (!d) continue;
      groups.admin.appendChild(
        el("path", {
          d,
          class: `admin-line${level >= 3 ? " lvl3" : ""}`,
          "fill-rule": "evenodd",
        }),
      );
    }

    // selected -------------------------------------------------------------
    groups.selected.replaceChildren();
    if (state.selected) {
      const d = geometryPath(state.selected.geometry, project);
      if (d) groups.selected.appendChild(el("path", { d, class: "selected-fill", "fill-rule": "evenodd" }));
    }

    // grids ----------------------------------------------------------------
    groups.grids.replaceChildren();
    for (const grid of state.grids) {
      const nw = project(grid.west, grid.north);
      const se = project(grid.east, grid.south);
      groups.grids.appendChild(
        el("rect", {
          x: Math.min(nw[0], se[0]),
          y: Math.min(nw[1], se[1]),
          width: Math.abs(se[0] - nw[0]),
          height: Math.abs(se[1] - nw[1]),
          class: "grid-line",
        }),
      );
    }

    // field ----------------------------------------------------------------
    groups.field.replaceChildren();
    if (state.field) {
      const geometry =
        state.field.type === "Feature" ? state.field.geometry : state.field;
      const d = geometryPath(geometry, project);
      if (d) groups.field.appendChild(el("path", { d, class: "field-fill", "fill-rule": "evenodd" }));
    }

    // points ---------------------------------------------------------------
    groups.points.replaceChildren();
    if (state.point) {
      const [x, y] = project(state.point.lon, state.point.lat);
      groups.points.appendChild(el("circle", { cx: x, cy: y, r: 7.5, class: "point-ring" }));
      groups.points.appendChild(el("circle", { cx: x, cy: y, r: 3.4, class: "point-dot" }));
    }

    // labels ---------------------------------------------------------------
    groups.labels.replaceChildren();
    for (const label of state.labels) {
      const [x, y] = project(label.lon, label.lat);
      if (x < -100 || x > width + 100 || y < -30 || y > height + 30) continue;
      const text = el("text", { x, y, class: "atlas-label", "text-anchor": "middle" });
      text.textContent = label.text;
      groups.labels.appendChild(text);
    }
    if (state.note) {
      const note = el("text", { x: 12, y: height - 12, class: "atlas-note" });
      note.textContent = state.note;
      groups.labels.appendChild(note);
    }
  }

  // Coalesce redraws on a short timer rather than requestAnimationFrame:
  // RAF is paused in background tabs, which would leave the atlas blank until
  // the tab is focused. A timer keeps pan, zoom and data updates honest even
  // when the page was opened in the background.
  function schedule() {
    if (timer) return;
    timer = setTimeout(() => {
      timer = 0;
      render();
    }, 16);
  }

  function zoomBy(delta, anchor) {
    const [ax, ay] = anchor || [width / 2, height / 2];
    const [lon, lat] = unproject(ax, ay);
    view.zoom = clamp(view.zoom + delta, MIN_ZOOM, MAX_ZOOM);
    const scale = worldSize();
    const lonMerc = ((lon + 180) / 360);
    const latMerc = mercatorY(lat);
    view.centerLon = lonMerc * 360 - 180 - ((ax - width / 2) / scale) * 360;
    view.centerLat = inverseMercatorY(clamp(latMerc - (ay - height / 2) / scale, 0, 1));
    normalizeCenter();
    markViewChanged();
    schedule();
  }

  function normalizeCenter() {
    while (view.centerLon > 180) view.centerLon -= 360;
    while (view.centerLon < -180) view.centerLon += 360;
    view.centerLat = clamp(view.centerLat, -78, 82);
  }

  // ---------------------------------------------------------------- pointer
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    try {
      svg.setPointerCapture(event.pointerId);
    } catch {
      /* synthetic or already-released pointer */
    }
    drag = { x: event.clientX, y: event.clientY, moved: 0 };
  });

  svg.addEventListener("pointermove", (event) => {
    if (!drag) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    drag.x = event.clientX;
    drag.y = event.clientY;
    drag.moved += Math.abs(dx) + Math.abs(dy);
    const scale = worldSize();
    view.centerLon -= (dx / scale) * 360;
    const centerMerc = mercatorY(view.centerLat) - dy / scale;
    view.centerLat = inverseMercatorY(clamp(centerMerc, 0.02, 0.98));
    normalizeCenter();
    markViewChanged();
    schedule();
  });

  svg.addEventListener("pointerup", (event) => {
    if (!drag) return;
    const wasClick = drag.moved < 5;
    drag = null;
    try {
      svg.releasePointerCapture(event.pointerId);
    } catch {
      /* pointer already released */
    }
    if (wasClick && onPoint) {
      const rect = svg.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * width;
      const y = ((event.clientY - rect.top) / rect.height) * height;
      const [lon, lat] = unproject(x, y);
      onPoint([lon, lat]);
    }
  });

  svg.addEventListener("pointercancel", () => {
    drag = null;
  });

  svg.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const rect = svg.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / rect.width) * width;
      const y = ((event.clientY - rect.top) / rect.height) * height;
      const delta = -Math.sign(event.deltaY) * 0.55;
      zoomBy(delta, [x, y]);
    },
    { passive: false },
  );

  svg.addEventListener("dblclick", (event) => {
    event.preventDefault();
    const rect = svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * width;
    const y = ((event.clientY - rect.top) / rect.height) * height;
    zoomBy(0.9, [x, y]);
  });

  const observer = new ResizeObserver(() => schedule());
  observer.observe(container);

  render();

  return {
    setData(partial) {
      state = { ...state, ...partial };
      schedule();
    },
    setDetail(level) {
      const next = Math.max(0, Math.min(3, Number(level) || 0));
      if (next === state.detail) return;
      state.detail = next;
      schedule();
    },
    flyTo(center, zoom) {
      if (Array.isArray(center)) {
        view.centerLon = center[0];
        view.centerLat = center[1];
      }
      if (Number.isFinite(zoom)) view.zoom = clamp(zoom, MIN_ZOOM, MAX_ZOOM);
      normalizeCenter();
      markViewChanged();
      schedule();
    },
    fitBBox(bbox, { padding = 34, maxZoom = 10 } = {}) {
      if (!Array.isArray(bbox) || bbox.length !== 4) return;
      const [west, south, east, north] = bbox;
      const midLon = (west + east) / 2;
      const midMerc = (mercatorY(south) + mercatorY(north)) / 2;
      const lonSpan = Math.max(0.0002, (east - west) / 360);
      const mercSpan = Math.max(0.0002, mercatorY(south) - mercatorY(north));
      const sizeForLon = (width - padding * 2) / lonSpan;
      const sizeForLat = (height - padding * 2) / mercSpan;
      const scale = Math.max(1, Math.min(sizeForLon, sizeForLat));
      view.zoom = clamp(Math.log2(scale / TILE), MIN_ZOOM, maxZoom);
      view.centerLon = midLon;
      view.centerLat = inverseMercatorY(midMerc);
      normalizeCenter();
      markViewChanged();
      schedule();
    },
    zoomIn() {
      zoomBy(0.8);
    },
    zoomOut() {
      zoomBy(-0.8);
    },
    getView() {
      return { center: [view.centerLon, view.centerLat], zoom: view.zoom };
    },
    destroy() {
      observer.disconnect();
      if (timer) clearTimeout(timer);
      timer = 0;
      container.innerHTML = "";
    },
  };
}
