"""Single Vercel Python entry point for the ORBITILL JSON APIs.

Public API paths are rewritten here by ``vercel.json``.  The handler then
delegates to the exact same implementation used by the local judge server.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse

from services.science_api.server import Handler as PlatformHandler


class handler(PlatformHandler):
    def _restore_public_api_path(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        route = query.pop("route", [None])[0]
        if not route:
            return
        self.path = f"/api/{route}"
        if query:
            self.path += "?" + urlencode(query, doseq=True)

    def do_GET(self) -> None:  # noqa: N802 - stdlib/Vercel interface
        self._restore_public_api_path()
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802 - stdlib/Vercel interface
        self._restore_public_api_path()
        super().do_POST()
