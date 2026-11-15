"""Minimal hypothetical-weather helpers so AquaSense results can be compared to observed rain.
FutureFields owns scenario design/economics; these helpers only guarantee correct *labelling*:
every modified row is tagged precip_type='hypothetical_scenario' and can never be mistaken for observed rain."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Optional

from .models import DailyWeather


def _tag(w: DailyWeather, precip: float, name: str) -> DailyWeather:
    return replace(w, precip_mm=precip, precip_source=f"SCENARIO:{name}", precip_type="hypothetical_scenario")


def scale_rainfall(rows, factor: float, start: Optional[date] = None, end: Optional[date] = None, name: str = "rain_x") -> list:
    if factor < 0:
        raise ValueError("factor must be >= 0")
    out = []
    for w in rows:
        if w.precip_mm is not None and (start is None or w.date >= start) and (end is None or w.date <= end):
            out.append(_tag(w, w.precip_mm * factor, f"{name}{factor:g}"))
        else:
            out.append(w)
    return out


def dry_spell(rows, start: date, days: int, name: str = "dry_spell") -> list:
    end = start + timedelta(days=days - 1)
    return [_tag(w, 0.0, f"{name}_{days}d") if start <= w.date <= end else w for w in rows]


def delay_rain(rows, shift_days: int, name: str = "delay") -> list:
    """Shift the precipitation series later by shift_days (first days get 0 mm). Whole series becomes hypothetical."""
    by = {w.date: w.precip_mm for w in rows}
    out = []
    for w in rows:
        src = by.get(w.date - timedelta(days=shift_days))
        p = 0.0 if src is None else src
        out.append(_tag(w, p, f"{name}{shift_days}d"))
    return out
