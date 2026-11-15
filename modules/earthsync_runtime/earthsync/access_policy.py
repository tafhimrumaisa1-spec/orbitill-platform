"""Source access policy: credentials, throttling, offline mode, size guards.

* No secret is ever embedded in code, URLs we record, logs, or evidence records.
* Earthdata credentials come only from the environment (``EARTHDATA_TOKEN``) and
  only for adapters whose manifest entry says ``earthdata_login``.
* Planet-scale downloads are refused by construction.
"""
from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import PlanetScaleDownloadRefused
from .schemas import Insufficiency, InsufficiencyCode

USER_AGENT = "ORBITILL-EarthSync-EvidenceFusion/0.1 (NASA Space Apps 2026 research prototype)"
SECRET_ENV_VARS = ("EARTHDATA_TOKEN", "EARTHDATA_PASSWORD", "NASS_API_KEY", "OPENET_API_KEY", "CDSAPI_KEY", "AMS_API_KEY")

_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+")
_QS_SECRET = re.compile(r"(?i)([?&](?:token|api[_-]?key|key|password|access_token)=)[^&\s]+")


def redact_secrets(text: str) -> str:
    """Remove bearer tokens, secret-looking query params and env secret values."""
    if not text:
        return text
    out = _BEARER.sub(r"\1[REDACTED]", text)
    out = _QS_SECRET.sub(r"\1[REDACTED]", out)
    for name in SECRET_ENV_VARS:
        val = os.environ.get(name)
        if val and len(val) >= 6:
            out = out.replace(val, "[REDACTED]")
    return out


def earthdata_token() -> str | None:
    """Return the Earthdata bearer token from the environment, or None. Never logged."""
    return os.environ.get("EARTHDATA_TOKEN") or None


def default_cache_dir() -> Path:
    return Path(os.environ.get("EARTHSYNC_CACHE_DIR", Path.home() / ".cache" / "earthsync"))


@dataclass
class AccessPolicy:
    offline: bool = field(default_factory=lambda: os.environ.get("EARTHSYNC_OFFLINE", "") in ("1", "true", "yes"))
    cache_dir: Path = field(default_factory=default_cache_dir)
    max_concurrent_requests: int = 5          # POWER tutorial: "do not go more than five concurrent requests"
    min_interval_s: float = 0.4               # polite spacing between requests to the same provider
    timeout_s: float = 45.0
    max_retries: int = 3
    max_bbox_area_deg2: float = 25.0          # anything larger is "planet-scale" for a farm tool
    max_download_mb: float = 50.0
    allow_synthetic_fixture: bool = False     # explicit opt-in; synthetic data is never silently served
    recent_data_ttl_days: float = 1.0         # POWER recent days are revised (NRT -> final)
    historical_ttl_days: float = 365.0

    def __post_init__(self) -> None:
        self._sem = threading.BoundedSemaphore(self.max_concurrent_requests)
        self._last = 0.0
        self._lock = threading.Lock()

    # --- throttling ---
    def acquire(self) -> None:
        self._sem.acquire()
        with self._lock:
            wait = self.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def release(self) -> None:
        self._sem.release()

    # --- size guards ---
    def guard_download(self, west: float, south: float, east: float, north: float, est_mb: float | None = None) -> None:
        area = abs(east - west) * abs(north - south)
        if area > self.max_bbox_area_deg2:
            raise PlanetScaleDownloadRefused(Insufficiency(
                code=InsufficiencyCode.resolution_mismatch,
                message=f"Refusing bbox of {area:.1f} deg^2 (> {self.max_bbox_area_deg2}). EarthSync fetches farm/region extracts only.",
                remedy="Request a farm-scale bbox or point; use a pre-built regional extract for maps."))
        if est_mb is not None and est_mb > self.max_download_mb:
            raise PlanetScaleDownloadRefused(Insufficiency(
                code=InsufficiencyCode.resolution_mismatch,
                message=f"Estimated download {est_mb:.0f} MB exceeds limit {self.max_download_mb:.0f} MB.",
                remedy="Subset by time/space/variable first."))
