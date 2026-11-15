"""Small local API for integration development and contract inspection."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import ThreadingHTTPServer
import mimetypes
import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .demo_compare import compare_barind_demo


ROOT = Path(__file__).resolve().parents[2]
from terralens.server import (  # noqa: E402
    Handler as TerraLensHandler,
    MAX_BODY as TERRALENS_MAX_BODY,
    envelope as terralens_envelope,
)
from terralens.types import Insufficiency, Status  # noqa: E402

REGIONS = ROOT / "config" / "regions.json"
WEB_ROOT = ROOT / "apps" / "web"


class Handler(TerraLensHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._json(200, {"status": "ok", "service": "orbitill-integration", "version": "0.2.0"})
            return
        if path == "/api/regions":
            self._json(200, json.loads(REGIONS.read_text(encoding="utf-8")))
            return
        if path.startswith("/api/terralens/"):
            route = "/api/" + path.removeprefix("/api/terralens/")
            self._api_get(route, parse_qs(parsed.query, keep_blank_values=True))
            return
        self._static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/terralens/field":
            self._terralens_field()
            return
        if path != "/api/demo/barind/compare":
            self._json(404, {"status": "not_found", "path": path})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384:
                self._json(413, {"status": "invalid_request", "message": "Request body is too large."})
                return
            body = json.loads(self.rfile.read(length) or b"{}")
            result = compare_barind_demo(
                rainfall_multiplier=body.get("rainfall_multiplier", 1.0),
                irrigation_allowance_mm=body.get("irrigation_allowance_mm", 700.0),
            )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"status": "invalid_request", "message": str(exc)})
            return
        self._json(200, result)

    def _terralens_field(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > TERRALENS_MAX_BODY:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE if length > TERRALENS_MAX_BODY else HTTPStatus.BAD_REQUEST,
                terralens_envelope(
                    Status.REFUSED,
                    None,
                    insufficiencies=[Insufficiency(
                        code="body_invalid",
                        message=f"Body must be 1..{TERRALENS_MAX_BODY} bytes of JSON.",
                        remedy='Send {"geometry": {...}} or {"lat": 24.37, "lon": 88.7}.',
                    )],
                ),
            )
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                terralens_envelope(
                    Status.REFUSED,
                    None,
                    insufficiencies=[Insufficiency(code="json_invalid", message="The request body is not valid JSON.")],
                ),
            )
            return
        if not isinstance(body, dict):
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                terralens_envelope(
                    Status.REFUSED,
                    None,
                    insufficiencies=[Insufficiency(code="json_shape", message="The request body must be a JSON object.")],
                ),
            )
            return
        self._api_field(body)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, value: object) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return

    def _static(self, request_path: str) -> None:
        relative = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
        candidate = (WEB_ROOT / relative).resolve()
        try:
            candidate.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self._json(403, {"status": "forbidden"})
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            self._json(404, {"status": "not_found", "path": request_path})
            return
        payload = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") or content_type in ("application/javascript", "image/svg+xml") else content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return


def serve(host: str | None = None, port: int | None = None) -> None:
    resolved_host = host or os.environ.get("HOST", "127.0.0.1")
    resolved_port = port if port is not None else int(os.environ.get("PORT", "8400"))
    ThreadingHTTPServer((resolved_host, resolved_port), Handler).serve_forever()


if __name__ == "__main__":
    serve()
