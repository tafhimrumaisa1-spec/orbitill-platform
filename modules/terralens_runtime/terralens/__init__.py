"""TerraLens Region Explorer — geography and region intelligence for ORBITILL.

Agent 03 module. Owns map UI, farm location selection, administrative geography
and the Region Intelligence Router. It does not own crop rules, NASA retrieval
or field validation.
"""
from __future__ import annotations

from .field import select_field
from .router import get_region_profile, region_packs
from .types import SCHEMA_VERSION

__version__ = "1.0.0"
__all__ = ["get_region_profile", "region_packs", "select_field", "SCHEMA_VERSION", "__version__"]
