/** MapLibre view for TerraLens.
 *
 *  The map owns only display concerns: bundled vector boundaries, pilot extents,
 *  native-grid footprints, the selected point/field, and optional NASA GIBS
 *  raster tiles at the catalogue's own tile-matrix level. It never fetches or
 *  interpolates environmental values.
 */

const GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const EMPTY = { type: "FeatureCollection", features: [] };
const RASTER_ID = "gibs-raster";

const BOUNDARY_FILES = {
  world: "world_countries.geojson",
  bd1: "bd_adm1.geojson",
  bd2: "bd_adm2.geojson",
  bd3: "bd_adm3.geojson",
  us1: "us_adm1.geojson",
  us2: "us_ia_adm2.geojson",
};

export const BOUNDARY_LAYER_IDS = [
  "bd1-line",
  "bd2-line",
  "bd3-line",
  "us1-line",
  "us2-line",
  "country-line",
];

function emptyCollection() {
  return { type: "FeatureCollection", features: [] };
}

function featureCollection(features) {
  return { type: "FeatureCollection", features: features.filter(Boolean) };
}

export async function createMapView(container, handlers = {}) {
  const maplibregl = await import("./vendor/maplibre/maplibre-gl.mjs");
  const reducedMotion =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const style = {
    version: 8,
    sources: {
      world: { type: "geojson", data: EMPTY },
      bd1: { type: "geojson", data: EMPTY },
      bd2: { type: "geojson", data: EMPTY },
      bd3: { type: "geojson", data: EMPTY },
      us1: { type: "geojson", data: EMPTY },
      us2: { type: "geojson", data: EMPTY },
      pilots: { type: "geojson", data: EMPTY },
      selected: { type: "geojson", data: EMPTY },
      grids: { type: "geojson", data: EMPTY },
      field: { type: "geojson", data: EMPTY },
      point: { type: "geojson", data: EMPTY },
      draw: { type: "geojson", data: EMPTY },
    },
    layers: [
      { id: "background", type: "background", paint: { "background-color": "#0b1d15" } },
      {
        id: "country-fill",
        type: "fill",
        source: "world",
        paint: { "fill-color": "#16352a", "fill-opacity": 0.92 },
      },
      {
        id: "pilot-fill",
        type: "fill",
        source: "pilots",
        paint: { "fill-color": "#c5ec58", "fill-opacity": 0.07 },
      },
      {
        id: "pilot-line",
        type: "line",
        source: "pilots",
        paint: { "line-color": "#c5ec58", "line-width": 1.5, "line-dasharray": [3, 2], "line-opacity": 0.9 },
      },
      {
        id: "selected-fill",
        type: "fill",
        source: "selected",
        paint: { "fill-color": "#c5ec58", "fill-opacity": 0.2 },
      },
      {
        id: "selected-line",
        type: "line",
        source: "selected",
        paint: { "line-color": "#c5ec58", "line-width": 2.4, "line-opacity": 0.95 },
      },
      {
        id: "grid-fill",
        type: "fill",
        source: "grids",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.09 },
      },
      {
        id: "grid-line",
        type: "line",
        source: "grids",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 1.4,
          "line-opacity": 0.85,
          "line-dasharray": [2, 2],
        },
      },
      {
        id: "country-line",
        type: "line",
        source: "world",
        paint: { "line-color": "#53745c", "line-width": 0.8, "line-opacity": 0.8 },
      },
      {
        id: "bd1-line",
        type: "line",
        source: "bd1",
        layout: { visibility: "none" },
        paint: { "line-color": "#89a98a", "line-width": 1.2, "line-opacity": 0.85 },
      },
      {
        id: "bd2-line",
        type: "line",
        source: "bd2",
        layout: { visibility: "none" },
        paint: { "line-color": "#b6cfa8", "line-width": 0.9, "line-opacity": 0.8 },
      },
      {
        id: "bd3-line",
        type: "line",
        source: "bd3",
        layout: { visibility: "none" },
        paint: { "line-color": "#c5ec58", "line-width": 0.55, "line-opacity": 0.42 },
      },
      {
        id: "us1-line",
        type: "line",
        source: "us1",
        layout: { visibility: "none" },
        paint: { "line-color": "#89a98a", "line-width": 1.1, "line-opacity": 0.8 },
      },
      {
        id: "us2-line",
        type: "line",
        source: "us2",
        layout: { visibility: "none" },
        paint: { "line-color": "#b6cfa8", "line-width": 0.9, "line-opacity": 0.8 },
      },
      {
        id: "field-fill",
        type: "fill",
        source: "field",
        paint: { "fill-color": "#d98e5c", "fill-opacity": 0.35 },
      },
      {
        id: "field-line",
        type: "line",
        source: "field",
        paint: { "line-color": "#f0ad7b", "line-width": 2.4 },
      },
      {
        id: "draw-line",
        type: "line",
        source: "draw",
        filter: ["==", ["geometry-type"], "LineString"],
        paint: { "line-color": "#c5ec58", "line-width": 2, "line-dasharray": [2, 1.4] },
      },
      {
        id: "draw-points",
        type: "circle",
        source: "draw",
        filter: ["==", ["geometry-type"], "Point"],
        paint: {
          "circle-radius": 3.6,
          "circle-color": "#c5ec58",
          "circle-stroke-color": "#0b1d15",
          "circle-stroke-width": 1.4,
        },
      },
      {
        id: "point-halo",
        type: "circle",
        source: "point",
        paint: {
          "circle-radius": 13,
          "circle-color": "#c5ec58",
          "circle-opacity": 0.14,
          "circle-stroke-color": "#c5ec58",
          "circle-stroke-opacity": 0.6,
          "circle-stroke-width": 1,
        },
      },
      {
        id: "point-dot",
        type: "circle",
        source: "point",
        paint: {
          "circle-radius": 5,
          "circle-color": "#c5ec58",
          "circle-stroke-color": "#0b1d15",
          "circle-stroke-width": 2,
        },
      },
    ],
  };

  const map = new maplibregl.Map({
    container,
    style,
    center: [88.6042, 24.3745],
    zoom: 6.4,
    minZoom: 1.4,
    maxZoom: 14,
    maxPitch: 0,
    dragRotate: false,
    pitchWithRotate: false,
    touchPitch: false,
    attributionControl: false,
    antialias: true,
    fadeDuration: 0,
    renderWorldCopies: true,
    canvasContextAttributes: { antialias: true },
  });

  let readyResolve;
  let readyReject;
  const ready = new Promise((resolve, reject) => {
    readyResolve = resolve;
    readyReject = reject;
  });

  const datasets = {};
  const loading = {};
  let countryCode = null;
  let detail = 0;
  let drawing = false;
  let drawVertices = [];
  let drawPreview = null;
  let rasterToken = 0;
  let rasterTimer = 0;
  let rasterSawData = false;
  let tileErrorReported = false;
  let currentLayer = null;
  let currentDate = null;
  let pilotMarkers = [];
  let pointMarker = null;
  let hoverFrame = 0;
  let destroyed = false;

  map.on("load", () => {
    readyResolve();
  });
  map.on("error", (event) => {
    if (destroyed) return;
    const sourceId = event && event.sourceId;
    if (sourceId === RASTER_ID && !tileErrorReported) {
      tileErrorReported = true;
      if (handlers.onTileError) handlers.onTileError("error");
    }
  });
  map.on("sourcedata", (event) => {
    if (event && event.sourceId === RASTER_ID && event.isSourceLoaded) {
      rasterSawData = true;
      if (rasterTimer) {
        clearTimeout(rasterTimer);
        rasterTimer = 0;
      }
    }
  });
  map.on("zoomend", () => applyVisibility());
  map.on("moveend", () => {
    if (handlers.onViewChange) handlers.onViewChange(getView());
  });

  // -------------------------------------------------------------- boundaries
  async function ensure(key) {
    if (!BOUNDARY_FILES[key]) return null;
    if (datasets[key]) return datasets[key];
    if (loading[key]) return loading[key];
    loading[key] = (async () => {
      try {
        const response = await fetch(`./data/admin/${BOUNDARY_FILES[key]}`, { cache: "force-cache" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const collection = await response.json();
        datasets[key] = collection;
        if (map.getSource(key)) map.getSource(key).setData(collection);
        return collection;
      } catch (error) {
        if (handlers.onBoundaryError) handlers.onBoundaryError(key, error);
        datasets[key] = null;
        return null;
      } finally {
        delete loading[key];
      }
    })();
    return loading[key];
  }

  function findFeature(id) {
    for (const key of Object.keys(datasets)) {
      const collection = datasets[key];
      if (!collection || !collection.features) continue;
      const hit = collection.features.find((feature) => feature.properties && feature.properties.id === id);
      if (hit) return hit;
    }
    return null;
  }

  function keysForAdmin(level) {
    if (countryCode === "BD") {
      return level === 1 ? ["bd1"] : level === 2 ? ["bd2"] : level === 3 ? ["bd3"] : [];
    }
    if (countryCode === "US") {
      return level === 1 ? ["us1"] : level === 2 ? ["us2"] : [];
    }
    return [];
  }

  async function loadCountry(code) {
    countryCode = code;
    await ensure("world");
    if (code === "BD") {
      await Promise.all([ensure("bd1"), ensure("bd2")]);
      // Upazila polygons are heavy; load them once the instrument is idle.
      const idle = window.requestIdleCallback || ((fn) => setTimeout(fn, 900));
      idle(() => ensure("bd3"), { timeout: 2500 });
    } else if (code === "US") {
      await ensure("us1");
    }
    applyVisibility();
  }

  function applyVisibility() {
    if (!map.getLayer("bd1-line")) return;
    const show = (id, on) => {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", on ? "visible" : "none");
    };
    const zoom = map.getZoom();
    show("bd1-line", detail >= 1);
    show("bd2-line", detail >= 2);
    show("bd3-line", detail >= 3 && zoom >= 7.1);
    show("us1-line", detail >= 1);
    show("us2-line", detail >= 2);
    show("country-line", detail < 2 || zoom < 6.4);
  }

  async function setSelectedAdmin(adminChain) {
    const deepest = adminChain && adminChain.length ? adminChain[adminChain.length - 1] : null;
    if (!deepest) {
      map.getSource("selected").setData(emptyCollection());
      return;
    }
    let feature = findFeature(deepest.id);
    if (!feature) {
      const keys = keysForAdmin(deepest.level);
      for (const key of keys) {
        // eslint-disable-next-line no-await-in-loop
        await ensure(key);
        feature = findFeature(deepest.id);
        if (feature) break;
      }
    }
    if (feature) {
      map.getSource("selected").setData({ type: "FeatureCollection", features: [feature] });
    } else {
      map.getSource("selected").setData(emptyCollection());
    }
  }

  async function setProfile(profile) {
    if (!profile) return;
    const { location, admin, region } = profile;
    if (location && !location.onLand) {
      map.getSource("selected").setData(emptyCollection());
    }
    if (countryCode !== location.countryCode) await loadCountry(location.countryCode);
    await setSelectedAdmin(admin || []);

    const pointFeature = {
      type: "Feature",
      properties: {},
      geometry: { type: "Point", coordinates: [location.lon, location.lat] },
    };
    map.getSource("point").setData(featureCollection([pointFeature]));

    if (!pointMarker) {
      const el = document.createElement("div");
      el.className = "point-label-marker";
      pointMarker = new maplibregl.Marker({ element: el, anchor: "bottom" })
        .setLngLat([location.lon, location.lat])
        .addTo(map);
    } else {
      pointMarker.setLngLat([location.lon, location.lat]);
    }
    pointMarker.getElement().textContent = `${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}`;

    const zoom = zoomForAdmin(admin, region);
    flyTo([location.lon, location.lat], zoom);
    await setPilots(region);
    return zoom;
  }

  function zoomForAdmin(admin, region) {
    if (region && region.extentBasis && region.regionId === "BD-RAJ-BARIND") return 7.6;
    if (region && region.regionId === "BD-COASTAL") return 7;
    if (region && region.regionId === "US-IA-STORY") return 8.4;
    const depth = admin ? admin.length : 0;
    if (depth >= 3) return 9.2;
    if (depth === 2) return 7.6;
    if (depth === 1) return 6.2;
    return countryCode === "BD" ? 6 : countryCode === "US" ? 3.8 : 2.6;
  }

  async function setPilots(region) {
    pilotMarkers.forEach((marker) => marker.remove());
    pilotMarkers = [];
    if (!region) {
      map.getSource("pilots").setData(emptyCollection());
      return;
    }
    const ids = region.admin2Ids || [];
    if (!ids.length) {
      map.getSource("pilots").setData(emptyCollection());
      return;
    }
    const collection = countryCode === "BD" ? await ensure("bd2") : await ensure("us2");
    if (!collection) return;
    const wanted = new Set(ids);
    const features = collection.features.filter((feature) => wanted.has(feature.properties.id));
    map.getSource("pilots").setData(featureCollection(features));

    const label = region.label;
    const el = document.createElement("div");
    el.className = "pilot-label-marker";
    el.textContent =
      (document.documentElement.lang === "bn" && region.labelBn ? region.labelBn : label)
        .split("·")[0]
        .trim();
    const bbox = region.bbox || [88.4, 24.4, 89.4, 25.4];
    const marker = new maplibregl.Marker({ element: el, anchor: "center" })
      .setLngLat([(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2])
      .addTo(map);
    pilotMarkers.push(marker);
  }

  // ------------------------------------------------------------------ layers
  function removeRaster() {
    rasterToken += 1;
    if (rasterTimer) {
      clearTimeout(rasterTimer);
      rasterTimer = 0;
    }
    if (map.getLayer(RASTER_ID)) map.removeLayer(RASTER_ID);
    if (map.getSource(RASTER_ID)) map.removeSource(RASTER_ID);
    currentLayer = null;
  }

  function setLayer(layer, date) {
    removeRaster();
    tileErrorReported = false;
    if (!layer) {
      if (handlers.onLayerState) handlers.onLayerState(null);
      return;
    }
    currentLayer = layer;
    currentDate = date;
    const datePart = layer.id === "srtm-elevation" ? "" : `/${date}`;
    const tileUrl = `${GIBS_BASE}/${layer.gibsLayer}/default${datePart}/${layer.matrixSet}/{z}/{y}/{x}.png`;
    const maxzoom = Math.min(Number(layer.matrixLevel) || 9, 12);
    const token = ++rasterToken;
    rasterSawData = false;

    map.addSource(RASTER_ID, {
      type: "raster",
      tiles: [tileUrl],
      tileSize: 256,
      minzoom: 0,
      maxzoom,
      attribution: layer.attribution,
    });
    const before = map.getLayer("country-line") ? "country-line" : undefined;
    map.addLayer(
      {
        id: RASTER_ID,
        type: "raster",
        source: RASTER_ID,
        paint: {
          "raster-opacity": 0.9,
          "raster-resampling": layer.group === "imagery" ? "nearest" : "linear",
          "raster-fade-duration": 0,
        },
      },
      before,
    );
    if (handlers.onLayerState) handlers.onLayerState(layer);

    rasterTimer = setTimeout(() => {
      if (token !== rasterToken || rasterSawData) return;
      if (!navigator.onLine) {
        if (handlers.onTileError) handlers.onTileError("offline");
        return;
      }
      if (handlers.onTileError) handlers.onTileError("timeout");
    }, 9000);
  }

  function setGrids(footprints, visible) {
    if (!footprints || !visible) {
      map.getSource("grids").setData(emptyCollection());
      return;
    }
    const features = Object.values(footprints).map((cell) => ({
      type: "Feature",
      properties: {
        grid: cell.grid,
        color: colorForGrid(cell.grid),
        cellId: cell.cellId,
      },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [cell.west, cell.south],
          [cell.east, cell.south],
          [cell.east, cell.north],
          [cell.west, cell.north],
          [cell.west, cell.south],
        ]],
      },
    }));
    map.getSource("grids").setData(featureCollection(features));
  }

  function colorForGrid(name) {
    if (/POWER meteorology/i.test(name)) return "#f5f3eb";
    if (/solar/i.test(name)) return "#ffd66e";
    if (/IMERG/i.test(name)) return "#7fd7ff";
    if (/SMAP/i.test(name)) return "#ffab7a";
    return "#d9e4d1";
  }

  function setField(geometry) {
    if (!geometry) {
      map.getSource("field").setData(emptyCollection());
      return;
    }
    map.getSource("field").setData({ type: "Feature", properties: {}, geometry });
    fitGeometry(geometry);
  }

  function fitGeometry(geometry) {
    let west = 180;
    let south = 90;
    let east = -180;
    let north = -90;
    const walk = (coords) => {
      if (!Array.isArray(coords)) return;
      if (typeof coords[0] === "number") {
        west = Math.min(west, coords[0]);
        east = Math.max(east, coords[0]);
        south = Math.min(south, coords[1]);
        north = Math.max(north, coords[1]);
        return;
      }
      coords.forEach(walk);
    };
    walk(geometry.coordinates);
    if (west <= east) {
      map.fitBounds([[west, south], [east, north]], {
        padding: { top: 90, bottom: 150, left: 70, right: 70 },
        maxZoom: 16,
        duration: reducedMotion ? 0 : 900,
      });
    }
  }

  // ------------------------------------------------------------------- draw
  function renderDraw() {
    const features = drawVertices.map(([lon, lat]) => ({
      type: "Feature",
      properties: {},
      geometry: { type: "Point", coordinates: [lon, lat] },
    }));
    const line = drawVertices.slice();
    if (line.length >= 2 || drawPreview) {
      const full = drawPreview ? [...line, drawPreview] : line;
      if (full.length >= 2) {
        features.push({
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: full },
        });
      }
    }
    map.getSource("draw").setData(featureCollection(features));
  }

  function startDraw() {
    drawing = true;
    drawVertices = [];
    drawPreview = null;
    map.doubleClickZoom.disable();
    map.getCanvas().style.cursor = "crosshair";
    if (handlers.onDrawState) handlers.onDrawState(true);
    renderDraw();
  }

  function cancelDraw() {
    drawing = false;
    drawVertices = [];
    drawPreview = null;
    map.doubleClickZoom.enable();
    map.getCanvas().style.cursor = "";
    map.getSource("draw").setData(emptyCollection());
    if (handlers.onDrawState) handlers.onDrawState(false);
  }

  function finishDraw() {
    if (!drawing) return null;
    if (drawVertices.length < 3) {
      if (handlers.onDrawTooFew) handlers.onDrawTooFew();
      return null;
    }
    const ring = drawVertices.map(([lon, lat]) => [Number(lon.toFixed(7)), Number(lat.toFixed(7))]);
    ring.push([...ring[0]]);
    const polygon = { type: "Polygon", coordinates: [ring] };
    cancelDraw();
    if (handlers.onDrawFinish) handlers.onDrawFinish(polygon);
    return polygon;
  }

  map.on("click", (event) => {
    if (drawing) {
      if (event.originalEvent && event.originalEvent.detail > 1) return;
      const { lng, lat } = event.lngLat;
      const last = drawVertices[drawVertices.length - 1];
      if (last && Math.abs(last[0] - lng) < 1e-7 && Math.abs(last[1] - lat) < 1e-7) return;
      drawVertices.push([lng, lat]);
      drawPreview = null;
      renderDraw();
      return;
    }
    if (handlers.onPoint) handlers.onPoint([event.lngLat.lng, event.lngLat.lat]);
  });

  map.on("dblclick", (event) => {
    if (!drawing) return;
    event.preventDefault();
    finishDraw();
  });

  map.on("mousemove", (event) => {
    if (drawing) {
      drawPreview = [event.lngLat.lng, event.lngLat.lat];
      renderDraw();
      return;
    }
    if (!handlers.onHover) return;
    if (hoverFrame) return;
    hoverFrame = requestAnimationFrame(() => {
      hoverFrame = 0;
      const layers = BOUNDARY_LAYER_IDS.filter((id) => map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none");
      let features = [];
      try {
        features = map.queryRenderedFeatures(event.point, { layers });
      } catch {
        features = [];
      }
      const hit = features.find((feature) => feature.properties && feature.properties.name);
      if (hit) {
        map.getCanvas().style.cursor = "pointer";
        handlers.onHover({
          x: event.point.x,
          y: event.point.y,
          name: hit.properties.name,
          nameBn: hit.properties.nameBn,
          id: hit.properties.id,
          level: hit.properties.level,
        });
      } else {
        if (!drawing) map.getCanvas().style.cursor = "";
        handlers.onHover(null);
      }
    });
  });

  map.getCanvas().addEventListener("mouseleave", () => {
    if (!drawing) map.getCanvas().style.cursor = "";
    if (handlers.onHover) handlers.onHover(null);
  });

  // ------------------------------------------------------------------ camera
  function flyTo(center, zoom) {
    map.flyTo({
      center,
      zoom,
      duration: reducedMotion ? 0 : 1250,
      essential: true,
    });
  }

  function getView() {
    const center = map.getCenter();
    return { center: [center.lng, center.lat], zoom: map.getZoom() };
  }

  const observer = new ResizeObserver(() => {
    if (!destroyed) map.resize();
  });
  observer.observe(container);

  return {
    map,
    ready,
    getView,
    getCenter() {
      return getView().center;
    },
    getZoom() {
      return map.getZoom();
    },
    setLocale() {
      // Boundary labels are DOM markers and are handled by the app.
    },
    ensure,
    setCountry(code) {
      return loadCountry(code);
    },
    setBoundaryDetail(level) {
      detail = Math.max(0, Math.min(3, Number(level) || 0));
      applyVisibility();
    },
    setProfile,
    setLayer,
    setGrids,
    setField,
    setPilots,
    startDraw,
    cancelDraw,
    finishDraw,
    isDrawing() {
      return drawing;
    },
    zoomIn() {
      map.zoomIn({ duration: reducedMotion ? 0 : 260 });
    },
    zoomOut() {
      map.zoomOut({ duration: reducedMotion ? 0 : 260 });
    },
    flyTo,
    fitBBox(bbox) {
      if (!bbox || bbox.length !== 4) return;
      map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], {
        padding: 60,
        maxZoom: 10,
        duration: reducedMotion ? 0 : 900,
      });
    },
    getCurrentLayer() {
      return currentLayer;
    },
    getCurrentDate() {
      return currentDate;
    },
    destroy() {
      destroyed = true;
      observer.disconnect();
      if (rasterTimer) clearTimeout(rasterTimer);
      pilotMarkers.forEach((marker) => marker.remove());
      map.remove();
    },
  };
}
