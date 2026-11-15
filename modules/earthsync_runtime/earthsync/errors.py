"""Typed exceptions. Each carries an ``Insufficiency`` so callers can hand a
structured 'we do not know' downstream instead of a stack trace or a guess."""
from __future__ import annotations

from .schemas import Insufficiency, InsufficiencyCode


class EarthSyncError(Exception):
    def __init__(self, insufficiency: Insufficiency):
        super().__init__(insufficiency.message)
        self.insufficiency = insufficiency


class SourceError(EarthSyncError):
    """Provider unreachable / rejected the request / returned something unusable."""


class OfflineCacheMiss(EarthSyncError):
    pass


class PlanetScaleDownloadRefused(EarthSyncError):
    pass


def make(code: InsufficiencyCode, message: str, cls: type[EarthSyncError] = SourceError, **kw) -> EarthSyncError:
    return cls(Insufficiency(code=code, message=message, **kw))
