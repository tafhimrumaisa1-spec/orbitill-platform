"""Lazy, read-only loader for the built boundary bundle.

The router needs three things from disk: an index of units without geometry,
the polygons for point-in-polygon checks, and the pilot extents. Geometry stays
in memory after first use (about 11 MB of JSON), which is fine for a local
research instrument and avoids a spatial-database dependency.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from . import geometry

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ADMIN = DATA / "admin"

BARIND_DISTRICTS = {
    "BD-ADM2-rajshahi", "BD-ADM2-chapainawabganj", "BD-ADM2-naogaon",
    "BD-ADM2-natore", "BD-ADM2-pabna", "BD-ADM2-sirajganj",
    "BD-ADM2-bogura", "BD-ADM2-joypurhat",
}
COASTAL_DISTRICTS = {
    "BD-ADM2-bagerhat", "BD-ADM2-barguna", "BD-ADM2-barishal", "BD-ADM2-bhola",
    "BD-ADM2-chandpur", "BD-ADM2-chattogram", "BD-ADM2-cox-s-bazar",
    "BD-ADM2-feni", "BD-ADM2-gopalganj", "BD-ADM2-jashore",
    "BD-ADM2-jhalakathi", "BD-ADM2-khulna", "BD-ADM2-lakshmipur",
    "BD-ADM2-narail", "BD-ADM2-noakhali", "BD-ADM2-patuakhali",
    "BD-ADM2-pirojpur", "BD-ADM2-satkhira", "BD-ADM2-shariatpur",
}


def norm(text: str | None) -> str:
    """Search-normalisation only; never used to rewrite a displayed name."""
    s = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class DataStore:
    def __init__(self, admin_dir: Path | None = None) -> None:
        self.admin_dir = admin_dir or ADMIN
        self.build_report = self._read_json(DATA / "build_report.json")
        self.index = self._read_json(self.admin_dir / "index.json")
        self.data_version: str = self.build_report.get("dataVersion", "unknown")

        self.bd_adm1 = self._features("bd_adm1.geojson")
        self.bd_adm2 = self._features("bd_adm2.geojson")
        self.bd_adm3 = self._features("bd_adm3.geojson")
        self.us_states = self._features("us_adm1.geojson")
        self.us_counties = self._features("us_ia_adm2.geojson")
        self.countries = self._features("world_countries.geojson")

        self.bd1_geom = self._prep(self.bd_adm1)
        self.bd2_geom = self._prep(self.bd_adm2)
        self.bd3_geom = self._prep(self.bd_adm3)
        self.us1_geom = self._prep(self.us_states)
        self.us2_geom = self._prep(self.us_counties)
        self.country_geom = self._prep(self.countries)

        self.units: dict[str, dict] = {}
        for group in self.index.get("units", {}).values():
            for unit in group:
                self.units[unit["id"]] = unit

        self.units_by_parent: dict[str, list[dict]] = {}
        for unit in self.units.values():
            self.units_by_parent.setdefault(unit.get("parentId") or "", []).append(unit)
        for values in self.units_by_parent.values():
            values.sort(key=lambda u: u["name"])

        self._country_by_code = {}
        for feature in self.countries:
            props = feature["properties"]
            code = props.get("countryCode")
            if code and code not in self._country_by_code:
                self._country_by_code[code] = feature

        self._pack_cache: dict[str, dict] = {}

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def _features(self, name: str) -> list[dict]:
        payload = self._read_json(self.admin_dir / name)
        return payload["features"]

    @staticmethod
    def _prep(features: list[dict]) -> list[tuple[dict, list[float]]]:
        out = []
        for feature in features:
            props = feature["properties"]
            box = props.get("bbox") or geometry.bbox_of_geom(feature["geometry"])
            out.append((feature, box))
        return out

    # ---------------------------------------------------------------- lookups
    def find_containing(self, prepared, lon: float, lat: float):
        for feature, box in prepared:
            if geometry.point_in_bbox(lon, lat, box) and geometry.point_in_geom(lon, lat, feature["geometry"]):
                return feature
        return None

    def country_at(self, lat: float, lon: float):
        return self.find_containing(self.country_geom, lon, lat)

    def country_by_code(self, code: str | None):
        if not code:
            return None
        return self._country_by_code.get(code.upper())

    def bd_chain(self, lat: float, lon: float) -> list[dict]:
        chain = []
        division = self.find_containing(self.bd1_geom, lon, lat)
        if not division:
            return chain
        chain.append(division)
        district = self.find_containing(self.bd2_geom, lon, lat)
        if district:
            chain.append(district)
            upazila = self.find_containing(self.bd3_geom, lon, lat)
            if upazila:
                chain.append(upazila)
        return chain

    def us_chain(self, lat: float, lon: float) -> list[dict]:
        chain = []
        state = self.find_containing(self.us1_geom, lon, lat)
        if not state:
            return chain
        chain.append(state)
        county = self.find_containing(self.us2_geom, lon, lat)
        if county:
            chain.append(county)
        return chain

    def unit(self, unit_id: str) -> dict | None:
        return self.units.get(unit_id)

    def children(self, parent_id: str) -> list[dict]:
        return self.units_by_parent.get(parent_id, [])

    # ------------------------------------------------------------- pilot packs
    @property
    def region_index(self) -> dict:
        return self.index.get("regions", {})

    def pack_extent(self, region_id: str) -> dict:
        if region_id in self._pack_cache:
            return self._pack_cache[region_id]

        entry = self.region_index.get(region_id, {})
        ids = entry.get("admin2Ids", [])
        features = [f for f in self.bd_adm2 if f["properties"]["id"] in ids]
        if region_id.startswith("US-IA"):
            features = [f for f in self.us_counties if f["properties"]["id"] in ids] or list(self.us_counties)

        if not features:
            if region_id.startswith("US-IA"):
                features = list(self.us_states)
            elif region_id.startswith("BD"):
                features = list(self.bd_adm1)
            else:
                features = []

        if features:
            boxes = [f["properties"]["bbox"] for f in features]
            bbox = [
                min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes),
            ]
            largest = max(features, key=lambda f: f["properties"].get("areaKm2") or 0)
            anchor = list(largest["properties"]["centroid"])
            area = round(sum(f["properties"].get("areaKm2") or 0 for f in features), 1)
        else:
            bbox, anchor, area = None, None, None

        payload = {
            "regionId": region_id,
            "admin2Ids": ids,
            "bbox": bbox,
            "anchor": anchor,
            "anchorNote": "Representative point of the largest member district" if features else None,
            "approxAreaKm2": area,
            "featureCount": len(features),
        }
        self._pack_cache[region_id] = payload
        return payload

    def resolve_region(self, country_code: str | None, admin: list[dict]) -> tuple[str, str]:
        """Return (region_id, reason). Never invents a region pack."""
        if country_code == "BD":
            district_ids = {u["properties"]["id"] for u in admin if u["properties"]["level"] == 2}
            if district_ids & BARIND_DISTRICTS:
                return "BD-RAJ-BARIND", "Point lies in a Barind pilot district (administrative proxy)."
            if district_ids & COASTAL_DISTRICTS:
                return "BD-COASTAL", "Point lies in a WARPO/World Bank coastal pilot district."
            return "BD-NATIONAL", "Bangladesh location outside the two pilot extents."
        if country_code == "US":
            states = [u for u in admin if u["properties"]["level"] == 1]
            counties = [u for u in admin if u["properties"]["level"] == 2]
            if any(u["properties"]["name"] == "Iowa" for u in states):
                if any(u["properties"]["name"] == "Story" for u in counties):
                    return "US-IA-STORY", "Point lies in Story County, the single US research pilot."
                return "US-IA", "Iowa location outside the Story County research pilot."
            return "US-NATIONAL", "US location outside the Iowa pilot; no US regional pack exists."
        if country_code:
            return "GLOBAL", "No regional pack for this country; global exploration only."
        return "GLOBAL", "Point is outside recognised land; only exploration context exists."

    # --------------------------------------------------------------- distance
    def distance_to_nearest_country_km(self, lat: float, lon: float) -> tuple[float | None, str | None]:
        best = None
        for feature in self.countries:
            props = feature["properties"]
            cx, cy = props["centroid"]
            rough = geometry.haversine_km((lon, lat), (cx, cy))
            if rough - (props["areaKm2"] ** 0.5) > 3500:
                continue
            distance = self._distance_to_geom_km(lon, lat, feature["geometry"])
            if best is None or distance < best[0]:
                best = (distance, props["name"])
        return (round(best[0], 1), best[1]) if best else (None, None)

    @staticmethod
    def _distance_to_geom_km(lon: float, lat: float, geom: dict) -> float:
        # Local equirectangular projection is accurate enough for a "nearest coast"
        # display at these distances.
        kx = geometry.KM_PER_DEG_LON_EQ * math.cos(math.radians(lat))
        ky = geometry.KM_PER_DEG_LAT
        px, py = lon * kx, lat * ky
        best = float("inf")
        for ring in geometry.iter_rings(geom):
            for i in range(len(ring) - 1):
                x1, y1 = ring[i][0] * kx, ring[i][1] * ky
                x2, y2 = ring[i + 1][0] * kx, ring[i + 1][1] * ky
                dx, dy = x2 - x1, y2 - y1
                length2 = dx * dx + dy * dy or 1e-12
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length2))
                qx, qy = x1 + t * dx, y1 + t * dy
                dist = math.hypot(px - qx, py - qy)
                if dist < best:
                    best = dist
        return best

    # ----------------------------------------------------------------- search
    def search(self, query: str, country_code: str | None = None, limit: int = 12) -> list[dict]:
        q = norm(query)
        raw = query.strip()
        if not raw:
            return []
        scored = []
        for unit in self.units.values():
            if country_code and unit["countryCode"] != country_code:
                continue
            names = [unit.get("name") or ""] + list(unit.get("aliases") or [])
            bn = unit.get("nameBn") or ""
            score = 0.0
            matched = None
            if q:
                for name in names:
                    n = norm(name)
                    if not n:
                        continue
                    if n == q:
                        score, matched = 100.0, name
                        break
                    if n.startswith(q):
                        score, matched = 80.0, name
                    elif q in n:
                        score, matched = 55.0, name
            if raw and bn and raw in bn:
                if score < 90:
                    score, matched = 90.0, bn
            if score:
                # Prefer the more specific unit at equal string match.
                score += unit["level"] * 2
                scored.append((score, unit, matched))
        scored.sort(key=lambda item: (-item[0], item[1]["name"]))
        out = []
        for score, unit, matched in scored[:limit]:
            region_id, _ = self._region_for_unit(unit)
            out.append({
                "id": unit["id"],
                "level": unit["level"],
                "countryCode": unit["countryCode"],
                "name": unit["name"],
                "nameBn": unit.get("nameBn"),
                "matchedName": matched,
                "centroid": unit["centroid"],
                "bbox": unit["bbox"],
                "areaKm2": unit.get("areaKm2"),
                "regionId": region_id,
            })
        return out

    def _region_for_unit(self, unit: dict) -> tuple[str, str]:
        if unit["countryCode"] == "BD":
            if unit["id"] in BARIND_DISTRICTS:
                return "BD-RAJ-BARIND", "Barind pilot district"
            if unit["id"] in COASTAL_DISTRICTS:
                return "BD-COASTAL", "Coastal pilot district"
            parent = unit.get("parentId")
            if parent in BARIND_DISTRICTS:
                return "BD-RAJ-BARIND", "Inside a Barind pilot district"
            if parent in COASTAL_DISTRICTS:
                return "BD-COASTAL", "Inside a coastal pilot district"
            return "BD-NATIONAL", "Bangladesh national context"
        if unit["countryCode"] == "US":
            if unit["id"] == "US-IA-ADM2-story":
                return "US-IA-STORY", "Story County research pilot"
            if unit["id"] == "US-IA" or unit.get("parentId") == "US-IA":
                return "US-IA", "Iowa pilot state"
            return "US-NATIONAL", "US exploration"
        return "GLOBAL", "Global exploration"


@lru_cache(maxsize=1)
def store() -> DataStore:
    return DataStore()
