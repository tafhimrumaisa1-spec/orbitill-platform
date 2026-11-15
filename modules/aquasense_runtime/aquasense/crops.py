"""Crop water-physics coefficient registry (loaded from data/coefficients.json).

AquaSense does not own crop RULES (SoilBrain does); this is the hydrological coefficient fixture and every
value carries source + status so integration can swap in SoilBrain's validated calendar.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .errors import UnsupportedCrop

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _raw() -> dict:
    return json.loads((DATA_DIR / "coefficients.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def sources() -> dict:
    return json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))


@dataclass
class StageDays:
    ini: int
    dev: int
    mid: int
    late: int

    @property
    def total(self) -> int:
        return self.ini + self.dev + self.mid + self.late


@dataclass
class CropWaterProfile:
    crop_id: str
    names: dict
    kind: str                      # upland | paddy
    region_scope: list
    kc_ini: float
    kc_mid: float
    kc_end: float
    height_m: float
    stages: StageDays
    water_sensitive_stages: list
    raw: dict                      # full JSON record (coefficient provenance)
    zr_min_m: float = 0.0
    zr_max_range_m: tuple = (0.0, 0.0)
    p_table22: float = 0.5
    notes: list = field(default_factory=list)

    @property
    def zr_max_nominal_m(self) -> float:
        lo, hi = self.zr_max_range_m
        return (lo + hi) / 2.0

    def stage_status(self) -> str:
        return self.raw["stage_days"]["status"]

    def provenance(self) -> list:
        """Flat list of coefficient records for ModelRun output."""
        out = []
        r = self.raw
        out.append({"coefficient": "kc(ini,mid,end)", "value": [self.kc_ini, self.kc_mid, self.kc_end],
                    "source_id": r["kc"]["source"], "locator": r["kc"]["locator"], "status": r["kc"]["status"],
                    "applicability": sources()[r["kc"]["source"]]["geographic_applicability"]})
        sd = r["stage_days"]
        out.append({"coefficient": "stage_days(ini,dev,mid,late)", "value": [self.stages.ini, self.stages.dev, self.stages.mid, self.stages.late],
                    "source_id": sd["source"], "locator": sd.get("locator", ""), "status": sd["status"], "note": sd.get("note", ""),
                    "applicability": sources()[sd["source"]]["geographic_applicability"]})
        if "root" in r:
            out.append({"coefficient": "root depth zr (m)", "value": {"min": self.zr_min_m, "max_range": list(self.zr_max_range_m)},
                        "source_id": r["root"]["zr_max_source"], "locator": r["root"]["zr_locator"],
                        "status": "published_reference (max) + engineering_assumption (min)"})
            out.append({"coefficient": "depletion fraction p (Table 22, ETc=5 mm/d)", "value": self.p_table22,
                        "source_id": "FAO56", "locator": r.get("p_locator", "Table 22"), "status": "published_reference"})
        return out


def _build(cid: str, r: dict) -> CropWaterProfile:
    sd = r["stage_days"]
    root = r.get("root", {})
    return CropWaterProfile(
        crop_id=cid, names=r["names"], kind=r["kind"], region_scope=r["region_scope"],
        kc_ini=r["kc"]["ini"], kc_mid=r["kc"]["mid"], kc_end=r["kc"]["end"], height_m=r["height_m"],
        stages=StageDays(sd["ini"], sd["dev"], sd["mid"], sd["late"]),
        water_sensitive_stages=r.get("water_sensitive_stages", ["mid"]), raw=r,
        zr_min_m=root.get("zr_min_m", 0.0), zr_max_range_m=tuple(root.get("zr_max_range_m", (0.0, 0.0))),
        p_table22=r.get("p_table22", 0.5))


def list_crops() -> list[str]:
    return sorted(_raw()["crops"])


def get_crop(crop_id: str, stage_days: Optional[dict] = None) -> CropWaterProfile:
    """Return a crop profile. `stage_days` overrides the placeholder calendar (e.g. from SoilBrain) and marks
    the stage-length provenance as 'external_validated_calendar'."""
    crops = _raw()["crops"]
    if crop_id not in crops:
        raise UnsupportedCrop(f"no water-physics profile for crop {crop_id!r}", supported=sorted(crops))
    r = json.loads(json.dumps(crops[crop_id]))  # deep copy
    if stage_days:
        sd = {k: int(stage_days[k]) for k in ("ini", "dev", "mid", "late")}
        if min(sd.values()) < 0 or sum(sd.values()) <= 0:
            raise UnsupportedCrop("invalid stage_days override", stage_days=stage_days)
        r["stage_days"] = {**sd, "source": stage_days.get("source", "FARMER_GROUND"),
                           "locator": stage_days.get("locator", "supplied by caller (SoilBrain calendar)"),
                           "status": stage_days.get("status", "external_validated_calendar")}
    return _build(crop_id, r)


def texture_range(texture_class: str) -> dict:
    t = _raw()["texture_classes"]
    if texture_class not in t or texture_class.startswith("_"):
        raise UnsupportedCrop(f"unknown texture class {texture_class!r}", supported=[k for k in t if not k.startswith("_")])
    return t[texture_class]


def texture_classes() -> list[str]:
    return [k for k in _raw()["texture_classes"] if not k.startswith("_")]
