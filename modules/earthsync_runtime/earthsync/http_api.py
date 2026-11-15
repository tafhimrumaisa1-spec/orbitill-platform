"""Minimal stdlib JSON HTTP wrapper (no extra dependencies). For local integration/dev.

  python -m earthsync.http_api --port 8404
  GET /health | /sources | /sources/<id> | /availability?country=BD&lat=..&lon=..
  GET /series?lat=..&lon=..&start=YYYY-MM-DD&end=..&vars=T2M,PRECTOTCORR&allow_synthetic=1
  GET /chains/demo?lat=..&lon=..&year=2024&allow_synthetic=1      -> chains + graph
  GET /evidence/<chain_or_feature_id>
Binds to 127.0.0.1 by default. Errors are typed JSON, never stack traces.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .service import EarthSync

ES = EarthSync()


def _q(qs, k, default=None):
    return qs.get(k, [default])[0]


class H(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj, default=lambda x: x.model_dump(mode="json") if hasattr(x, "model_dump") else str(x)).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        try:
            if u.path == "/health":
                return self._send(200, {"ok": True, "module": "earthsync-evidencefusion"})
            if u.path == "/sources":
                return self._send(200, ES.list_sources())
            if u.path.startswith("/sources/"):
                try:
                    return self._send(200, ES.get_source_metadata(u.path.split("/", 2)[2]))
                except KeyError:
                    return self._send(404, {"error": "unknown_source"})
            if u.path == "/availability":
                return self._send(200, ES.get_data_availability(_q(qs, "country", "BD"), float(_q(qs, "lat")), float(_q(qs, "lon"))))
            if u.path == "/series":
                r = ES.get_environmental_series(float(_q(qs, "lat")), float(_q(qs, "lon")), _q(qs, "start"), _q(qs, "end"), tuple(_q(qs, "vars", "T2M,PRECTOTCORR").split(",")),
                                                allow_fixture=_q(qs, "allow_synthetic") == "1")
                return self._send(200 if r.status != "insufficient" else 422, r)
            if u.path == "/chains/demo":
                year = int(_q(qs, "year", "2024"))
                r = ES.get_environmental_series(float(_q(qs, "lat")), float(_q(qs, "lon")), f"{year}-01-01", f"{year}-12-31", ("T2M_MAX", "PRECTOTCORR"), allow_fixture=_q(qs, "allow_synthetic") == "1")
                if r.status == "insufficient":
                    return self._send(422, r)
                return self._send(200, ES.demo_chains(ES.series_objects(r), year))
            if u.path.startswith("/evidence/"):
                r = ES.get_evidence_for_calculation(u.path.split("/", 2)[2])
                return self._send(200 if r.status != "insufficient" else 404, r)
            return self._send(404, {"error": "not_found"})
        except (KeyError, ValueError, TypeError) as e:
            return self._send(400, {"error": "bad_request", "detail": str(e)})

    def log_message(self, *a):  # quiet; URLs may contain coordinates
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8404)
    a = ap.parse_args()
    ThreadingHTTPServer((a.host, a.port), H).serve_forever()


if __name__ == "__main__":
    main()
