"""Bundled offline fixtures, with two *distinct* kinds that can never be confused.

* ``real_retrieval``  - written only by ``scripts/fetch_real_fixtures.py`` after a live
  POWER response; carries fetch URL, UTC time, HTTP status and payload SHA-256.
* ``synthetic_demo``  - written only by ``scripts/make_synthetic_fixture.py``; carries
  a prominent warning and is served only when the caller explicitly opts in.

A fixture is served only if its POWER meteorology cell AND solar cell equal the
requested ones - a Rajshahi fixture is never returned for another place.
"""
from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .adapters.nasa_power import PowerFetch, PowerRequest
from .cache import canonical_json, sha256_text
from .errors import EarthSyncError
from .schemas import Insufficiency, InsufficiencyCode


def default_fixture_dir() -> Path:
    env = os.environ.get("EARTHSYNC_FIXTURE_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "fixtures"


@dataclass
class FixtureHit:
    fetch: PowerFetch
    kind: str  # real_retrieval | synthetic_demo
    path: Path
    meta: dict


def _load(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def list_fixtures(root: Optional[Path] = None) -> list[tuple[Path, dict]]:
    root = Path(root) if root else default_fixture_dir()
    out = []
    # The fetch script accepts an arbitrary output directory and writes fixtures
    # directly into it, while the repository's bundled fixtures live in typed
    # subdirectories. Support both layouts so a successful retrieval cannot be
    # silently ignored by the offline service.
    for d in (root, root / "real", root / "synthetic"):
        if d.exists():
            for p in sorted(list(d.glob("*.json")) + list(d.glob("*.json.gz"))):
                if p.name.startswith("FETCH_REPORT"):
                    continue
                try:
                    out.append((p, _load(p)))
                except (OSError, json.JSONDecodeError):
                    continue
    return out


def find_fixture(req: PowerRequest, *, allow_synthetic: bool, root: Optional[Path] = None) -> FixtureHit:
    """Return the best matching fixture or raise EarthSyncError with a typed reason."""
    want_met, want_sol = req.cells()
    reasons: list[str] = []
    for path, doc in list_fixtures(root):
        meta = doc.get("_fixture", {})
        kind = meta.get("kind")
        r = meta.get("request", {})
        try:
            fixture_req = PowerRequest(r["lat"], r["lon"], _d(r["start"]), _d(r["end"]), tuple(r["parameters"]),
                                       r.get("community", "AG"), r.get("time_standard"))
        except Exception:
            continue
        f_met, f_sol = fixture_req.cells()
        if f_met.cell_id != want_met.cell_id or f_sol.cell_id != want_sol.cell_id:
            reasons.append(f"{path.name}: different grid cell")
            continue
        if not set(req.parameters) <= set(fixture_req.parameters):
            reasons.append(f"{path.name}: lacks parameters {sorted(set(req.parameters) - set(fixture_req.parameters))}")
            continue
        if fixture_req.start > req.start or fixture_req.end < req.end:
            reasons.append(f"{path.name}: dates {fixture_req.start}..{fixture_req.end} do not cover request")
            continue
        if kind == "synthetic_demo" and not allow_synthetic:
            raise EarthSyncError(Insufficiency(
                code=InsufficiencyCode.synthetic_data_not_allowed,
                message=f"Only SYNTHETIC demonstration data is bundled for this location ({path.name}); "
                        "refusing to serve it as if it were NASA data.",
                remedy="Run scripts/fetch_real_fixtures.py on a networked machine, or pass allow_synthetic_fixture=True "
                       "for a clearly-labelled demo."))
        payload = doc["payload"]
        fetch_meta = meta.get("fetch", {})
        sha = fetch_meta.get("payload_sha256") or sha256_text(canonical_json(payload))
        mode = "fixture_real" if kind == "real_retrieval" else "fixture_synthetic"
        return FixtureHit(
            PowerFetch(payload, fetch_meta.get("url") or "synthetic://generated", fetch_meta.get("retrieved_at_utc") or meta.get("created_utc", ""),
                       mode, sha), kind, path, meta)
    raise EarthSyncError(Insufficiency(
        code=InsufficiencyCode.fixture_location_mismatch,
        message="No bundled fixture covers this location/date range/parameter set" + (f" ({'; '.join(reasons)})" if reasons else "."),
        remedy="Fetch live (network required) or add a real fixture for this grid cell."))


def _d(s: str):
    from datetime import date
    return date.fromisoformat(s)
