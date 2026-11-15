"""Tiny content-addressed JSON cache for provider responses."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def key_hash(parts: Any) -> str:
    return sha256_text(canonical_json(parts))[:32]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ResponseCache:
    def __init__(self, directory: Path):
        self.dir = Path(directory)

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> Optional[dict]:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None  # corrupt entry == miss; never serve half-written data

    def put(self, key: str, *, url: str, payload: Any, retrieved_at_utc: str, meta: Optional[dict] = None) -> dict:
        self.dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "key": key,
            "url": url,
            "retrieved_at_utc": retrieved_at_utc,
            "payload_sha256": sha256_text(canonical_json(payload)),
            "meta": meta or {},
            "payload": payload,
        }
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(entry), encoding="utf-8")
        tmp.replace(self._path(key))  # atomic
        return entry

    @staticmethod
    def age_days(entry: dict, now: Optional[datetime] = None) -> float:
        now = now or datetime.now(timezone.utc)
        t = datetime.strptime(entry["retrieved_at_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return (now - t).total_seconds() / 86400.0

    def list_entries(self) -> list[dict]:
        out = []
        if self.dir.exists():
            for p in sorted(self.dir.glob("*.json")):
                try:
                    out.append(json.loads(p.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return out
