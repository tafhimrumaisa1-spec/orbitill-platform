"""Stdlib HTTP service for the TerraLens Region Explorer.

Endpoints (all JSON under ``/api``):

  GET  /api/health
  GET  /api/config
  GET  /api/regions
  GET  /api/profile?lat=&lon=[&locale=&region=]
  GET  /api/search?q=[&country=&limit=]
  GET  /api/layers[?country=]
  GET  /api/sources
  POST /api/field        body: {"geometry": GeoJSON} | {"lat":..,"lon":..}

Static files are served from ``web/`` (UI) and ``data/admin/`` (GeoJSON).
No third-party Python packages, no API keys, no outbound requests at runtime.
"""
from __future__ import annotations

import json
import mimetypes
import posixpath
import threading
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import catalog, data, field, router
from .types import Insufficiency, SCHEMA_VERSION, Status

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA_ADMIN = ROOT / "data" / "admin"
ENVELOPE_SCHEMA = "terralens.envelope.v1"
MAX_BODY = 2 * 1024 * 1024
ALLOWED_LOCALES = {"en", "bn"}

MIME_OVERRIDES = {
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".geojson": "application/geo+json",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".woff2": "font/woff2",
    ".png": "image/png",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
}


def envelope(
    status: Status,
    data_payload=None,
    *,
    insufficiencies: list[Insufficiency] | None = None,
    warnings: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict:
    return {
        "schemaVersion": ENVELOPE_SCHEMA,
        "status": status.value,
        "data": data_payload,
        "insufficiencies": [i.to_dict() for i in (insufficiencies or [])],
        "warnings": warnings or [],
        "limitations": limitations or [],
        "isSynthetic": False,
    }


def _error(status: Status, code: str, message: str, remedy: str | None = None, http: int = 400) -> tuple[int, dict]:
    return http, envelope(
        status,
        None,
        insufficiencies=[Insufficiency(code=code, message=message, remedy=remedy)],
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "TerraLens/1.0"
    protocol_version = "HTTP/1.1"

    # -------------------------------------------------------------- plumbing
    def log_message(self, fmt, *args):  # noqa: A003 - stdlib signature
        if getattr(self.server, "quiet", False):
            return
        super().log_message(fmt, *args)

    def _send_json(self, code: int, payload: dict, *, cache: str = "no-store") -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_file(self, path: Path, *, cache: str = "public, max-age=300") -> None:
        if not path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, envelope(
                Status.REFUSED,
                None,
                insufficiencies=[Insufficiency(
                    code="not_found",
                    message=f"No such file: {path.name}",
                )],
            ))
            return
        suffix = path.suffix.lower()
        mime = MIME_OVERRIDES.get(suffix) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self._cors()
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def _safe_path(self, base: Path, relative: str) -> Path | None:
        relative = posixpath.normpath("/" + relative).lstrip("/")
        if relative.startswith(".."):
            return None
        candidate = (base / relative).resolve()
        try:
            candidate.relative_to(base.resolve())
        except ValueError:
            return None
        return candidate

    # ----------------------------------------------------------------- verbs
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query, keep_blank_values=True)
        try:
            if route.startswith("/api/"):
                self._api_get(route, query)
                return
            if route in ("/", "/index.html"):
                self._send_file(WEB / "index.html", cache="no-cache")
                return
            if route.startswith("/data/admin/"):
                target = self._safe_path(DATA_ADMIN, route[len("/data/admin/"):])
                self._send_file(target) if target else self._send_json(HTTPStatus.NOT_FOUND, envelope(Status.REFUSED, None))
                return
            if route.startswith("/data/"):
                target = self._safe_path(ROOT / "data", route[len("/data/"):])
                if target and target.suffix == ".json":
                    self._send_file(target)
                else:
                    self._send_json(HTTPStatus.NOT_FOUND, envelope(Status.REFUSED, None))
                return
            target = self._safe_path(WEB, route.lstrip("/"))
            if target is None:
                self._send_json(HTTPStatus.NOT_FOUND, envelope(Status.REFUSED, None))
                return
            if target.is_dir():
                target = target / "index.html"
            self._send_file(target)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, envelope(
                Status.REFUSED,
                None,
                insufficiencies=[Insufficiency(
                    code="server_error",
                    message="The request failed inside TerraLens.",
                    remedy="Check the server log; the request was not retried automatically.",
                )],
            ))

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/field":
            self._send_json(HTTPStatus.NOT_FOUND, envelope(Status.REFUSED, None))
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            code, payload = _error(
                Status.REFUSED,
                "body_invalid",
                f"Body must be 1..{MAX_BODY} bytes of JSON.",
                'Send {"geometry": {...}} or {"lat": 24.37, "lon": 88.7}.',
                http=413 if length > MAX_BODY else 400,
            )
            self._send_json(code, payload)
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, envelope(
                Status.REFUSED,
                None,
                insufficiencies=[Insufficiency(code="json_invalid", message="The request body is not valid JSON.")],
            ))
            return
        if not isinstance(body, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, envelope(
                Status.REFUSED,
                None,
                insufficiencies=[Insufficiency(code="json_shape", message="The request body must be a JSON object.")],
            ))
            return
        self._api_field(body)

    # ------------------------------------------------------------------- api
    def _api_get(self, route: str, query: dict) -> None:
        if route == "/api/health":
            store = data.store()
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {
                "service": "terralens-region-explorer",
                "schemaVersion": SCHEMA_VERSION,
                "dataVersion": store.data_version,
                "counts": store.index.get("counts", {}),
                "regions": list(catalog.REGION_PACKS),
                "layers": len(catalog.RASTER_LAYERS) + len(catalog.BOUNDARY_LAYERS) + 1,
                "sources": len(catalog.SOURCES),
                "serverTimeUtc": router.utcnow(),
            }))
            return

        if route == "/api/config":
            packs = router.region_packs()
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {
                "dataVersion": data.store().data_version,
                "defaultRegionId": "BD-NATIONAL",
                "defaultLocale": "en",
                "locales": ["en", "bn"],
                "regionPacks": packs,
                "layerGroups": {
                    "boundaries": "Administrative boundaries",
                    "pilot": "Pilot extents",
                    "vegetation": "Vegetation",
                    "water": "Water & rainfall",
                    "soil": "Soil moisture",
                    "imagery": "Imagery & reflectance",
                    "terrain": "Terrain",
                    "climate_grid": "Climate grid",
                },
                "continuousCoverageNote": (
                    "All environmental layers are gridded products. A 9 km SMAP cell, an 11 km IMERG "
                    "cell and a 30 m HLS pixel are not farm measurements."
                ),
            }))
            return

        if route == "/api/regions":
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {"regions": router.region_packs()}))
            return

        if route == "/api/layers":
            country = (query.get("country", [None])[0] or "").upper() or None
            layers = catalog.all_layers(country if country in ("BD", "US") else None)
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {
                "layers": [layer.to_dict() for layer in layers],
                "gibsBaseUrl": catalog.GIBS_URL,
                "attribution": "NASA GIBS / NASA EOSDIS; boundaries: geoBoundaries, Natural Earth",
            }))
            return

        if route == "/api/sources":
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {
                "schemaVersion": catalog.SCHEMA_VERSION,
                "sources": [s.to_dict() for s in catalog.SOURCES.values()],
            }))
            return

        if route == "/api/search":
            q = (query.get("q", [""])[0] or "").strip()
            country = (query.get("country", [None])[0] or "").upper() or None
            try:
                limit = max(1, min(30, int(query.get("limit", ["12"])[0])))
            except ValueError:
                limit = 12
            if not q:
                self._send_json(HTTPStatus.OK, envelope(Status.OK, {"query": q, "results": []}))
                return
            results = data.store().search(q, country if country in ("BD", "US") else None, limit)
            self._send_json(HTTPStatus.OK, envelope(Status.OK, {"query": q, "results": results}))
            return

        if route == "/api/profile":
            self._api_profile(query)
            return

        self._send_json(HTTPStatus.NOT_FOUND, envelope(
            Status.REFUSED,
            None,
            insufficiencies=[Insufficiency(code="unknown_endpoint", message=f"No API route {route!r}.")],
        ))

    def _api_profile(self, query: dict) -> None:
        region = (query.get("region", [None])[0] or "").strip() or None
        locale = (query.get("locale", ["en"])[0] or "en").lower()
        if locale not in ALLOWED_LOCALES:
            locale = "en"

        lat_raw = query.get("lat", [None])[0]
        lon_raw = query.get("lon", [None])[0]
        if lat_raw in (None, "") or lon_raw in (None, ""):
            if region and region in catalog.REGION_PACKS:
                anchor = next(
                    (pack["representativePoint"] for pack in router.region_packs() if pack["regionId"] == region),
                    None,
                )
                if not anchor:
                    code, payload = _error(
                        Status.REFUSED,
                        "region_without_anchor",
                        f"Region {region} has no representative point; supply lat and lon.",
                    )
                    self._send_json(code, payload)
                    return
                lat, lon = float(anchor[1]), float(anchor[0])
            else:
                code, payload = _error(
                    Status.REFUSED,
                    "coordinate_missing",
                    "Supply lat and lon (WGS84 decimal degrees).",
                    "Example: /api/profile?lat=24.3745&lon=88.6042",
                )
                self._send_json(code, payload)
                return
        else:
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except ValueError:
                code, payload = _error(
                    Status.REFUSED,
                    "coordinate_invalid",
                    "lat and lon must be decimal numbers.",
                )
                self._send_json(code, payload)
                return

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            code, payload = _error(
                Status.REFUSED,
                "coordinate_out_of_range",
                "Latitude must be -90..90 and longitude -180..180.",
            )
            self._send_json(code, payload)
            return

        profile = router.get_region_profile(lat, lon, locale=locale, requested_region=region)
        self._send_json(HTTPStatus.OK, envelope(
            Status.OK,
            profile.to_dict(),
            warnings=profile.warnings,
            limitations=profile.limitations,
        ))

    def _api_field(self, body: dict) -> None:
        locale = str(body.get("locale") or "en").lower()
        if locale not in ALLOWED_LOCALES:
            locale = "en"
        region = body.get("region") or body.get("requestedRegionId")

        geometry_payload = body.get("geometry")
        if geometry_payload is None and body.get("type") in ("Polygon", "MultiPolygon"):
            geometry_payload = body
        if geometry_payload is None and isinstance(body.get("feature"), dict):
            feature = body["feature"]
            geometry_payload = feature.get("geometry") if feature.get("type") == "Feature" else feature
        if isinstance(geometry_payload, dict) and geometry_payload.get("type") == "Feature":
            geometry_payload = geometry_payload.get("geometry")

        lat = body.get("lat")
        lon = body.get("lon")
        try:
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            code, payload = _error(Status.REFUSED, "coordinate_invalid", "lat and lon must be decimal numbers.")
            self._send_json(code, payload)
            return

        selection = field.select_field(
            geometry_payload=geometry_payload,
            lat=lat,
            lon=lon,
            requested_region=region,
            locale=locale,
        )
        status = Status.OK if selection.status == Status.OK else Status.REFUSED
        self._send_json(
            HTTPStatus.OK if status == Status.OK else HTTPStatus.UNPROCESSABLE_ENTITY,
            envelope(
                status,
                selection.to_dict(),
                insufficiencies=selection.insufficiencies,
                warnings=selection.warnings,
            ),
        )


class TerraLensServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler=Handler, quiet: bool = False):
        super().__init__(address, handler)
        self.quiet = quiet


def make_server(host: str = "127.0.0.1", port: int = 8765, quiet: bool = False) -> TerraLensServer:
    return TerraLensServer((host, port), quiet=quiet)


def serve(host: str = "127.0.0.1", port: int = 8765, quiet: bool = False) -> None:
    server = make_server(host, port, quiet=quiet)
    url_host = "localhost" if host in ("127.0.0.1", "0.0.0.0") else host
    print(f"TerraLens Region Explorer  http://{url_host}:{server.server_address[1]}/")
    print(f"  data version {data.store().data_version}")
    print("  Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()


def serve_in_thread(host: str = "127.0.0.1", port: int = 0) -> tuple[TerraLensServer, threading.Thread]:
    server = make_server(host, port, quiet=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
