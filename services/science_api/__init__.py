"""ORBITILL science integration bootstrap.

The public repository vendors the audited runtime packages under ``modules`` so
local development, GitHub clones and Vercel functions use the same code without
depending on private sibling handoff folders.
"""

from __future__ import annotations

from pathlib import Path
import sys


PLATFORM_ROOT = Path(__file__).resolve().parents[2]
for runtime in ("earthsync_runtime", "aquasense_runtime", "terralens_runtime"):
    path = str(PLATFORM_ROOT / "modules" / runtime)
    if path not in sys.path:
        sys.path.insert(0, path)
