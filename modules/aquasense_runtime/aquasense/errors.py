"""Typed errors. Malformed input raises; scientific insufficiency is returned as a status, not raised."""
from __future__ import annotations


class AquaSenseError(Exception):
    """Base error carrying a machine-readable code and structured details."""

    code = "AQUASENSE_ERROR"

    def __init__(self, message: str, **details):
        super().__init__(message)
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message, "details": self.details}


class InvalidInput(AquaSenseError):
    code = "INVALID_INPUT"


class UnitError(AquaSenseError):
    code = "UNIT_ERROR"


class ChronologyError(AquaSenseError):
    code = "CHRONOLOGY_ERROR"


class UnsupportedCrop(AquaSenseError):
    code = "UNSUPPORTED_CROP"
