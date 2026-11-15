"""camelCase service boundary expected by the shared integration contract (JSON in -> JSON out).

Each function accepts/returns plain dicts so Codex can host them behind HTTP, a worker, or a Python bridge:
  evaluateWaterBalance(request) ; estimateCropET(request) ; applyFarmEvent(request) ; getFarmState(request) ;
  getFarmAlerts(request) ; replayFarmTimeline(request) ; answerDoINeedWater(request)
See examples/ for request/response samples and schemas/ for JSON Schema."""
from __future__ import annotations

from datetime import date
from typing import Any

from .errors import AquaSenseError, InvalidInput
from .models import (DailyWeather, FarmConstraints, FarmEvent, FarmProfile, SoilProfile)
from .twin import FarmTwin, _event_id, apply_farm_event as _apply, evaluate_water_balance as _eval, get_farm_state as _state
from .alerts import get_farm_alerts as _alerts
from .replay import replay_farm_timeline as _replay
from .season import estimate_crop_et as _et, estimate_season_irrigation as _season


def _date(v) -> date:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(v)
    except Exception:
        raise InvalidInput("expected ISO date YYYY-MM-DD", value=v)


_WX = {f for f in DailyWeather.__dataclass_fields__}


def weather_from_dicts(rows) -> list:
    out = []
    for r in rows:
        r = dict(r)
        r["date"] = _date(r["date"])
        bad = set(r) - _WX
        if bad:
            raise InvalidInput("unknown weather fields", fields=sorted(bad))
        out.append(DailyWeather(**r))
    return out


def event_from_dict(e: dict) -> FarmEvent:
    return FarmEvent(date=_date(e["date"]), kind=e["kind"], payload=dict(e.get("payload", {})),
                     source=e.get("source", "farmer_reported"), recorded_at=e.get("recorded_at", ""), event_id=e.get("event_id", ""))


def profile_from_dict(p: dict) -> FarmProfile:
    soil = SoilProfile(**p.get("soil", {}))
    con = FarmConstraints(**p.get("constraints", {}))
    keys = {k: v for k, v in p.items() if k not in ("soil", "constraints")}
    return FarmProfile(soil=soil, constraints=con, **keys)


def twin_from_dict(d: dict) -> FarmTwin:
    t = FarmTwin(profile=profile_from_dict(d["profile"]), stage_days_override=d.get("stage_days_override"))
    t = t.with_weather(weather_from_dicts(d.get("weather", [])))
    for e in d.get("events", []):
        t = _apply(t, event_from_dict(e))
    return t


def _guard(fn):
    def wrapper(request: dict) -> dict:
        try:
            return fn(request)
        except AquaSenseError as ex:
            return ex.to_dict()
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


@_guard
def evaluateWaterBalance(request: dict) -> dict:
    """{twin, as_of, include_daily?, policy?} -> WaterBalanceResult"""
    return _eval(twin_from_dict(request["twin"]), _date(request["as_of"]), include_daily=request.get("include_daily", False),
                 policy=request.get("policy"))


@_guard
def answerDoINeedWater(request: dict) -> dict:
    """{twin, as_of} -> the farmer question 'Do I need water?' (verification_needed if inputs are missing)"""
    r = _eval(twin_from_dict(request["twin"]), _date(request["as_of"]))
    return {"as_of": r["as_of"], "status": r["status"], "readiness": r["readiness"], "answer": r["answer"],
            "assumptions": r["assumptions"], "blockers": r["blockers"], "model_version": r["model_version"], "input_hash": r["input_hash"]}


@_guard
def estimateCropET(request: dict) -> dict:
    """{farm, weather, crop_id, planting_date, stage_days?, season_irrigation?: bool} -> crop ET (+ policy irrigation need)"""
    farm = profile_from_dict(request["farm"])
    wx = weather_from_dicts(request["weather"])
    pd = _date(request["planting_date"])
    out = _et(request["crop_id"], farm, wx, pd, request.get("stage_days"))
    if request.get("season_irrigation"):
        out["season_irrigation"] = _season(request["crop_id"], farm, wx, pd, stage_days=request.get("stage_days"))
    return out


@_guard
def applyFarmEvent(request: dict) -> dict:
    """{twin, event} -> {twin, event_id}  (event-sourced; returns the new twin)"""
    ev = event_from_dict(request["event"])
    t = _apply(twin_from_dict(request["twin"]), ev)
    eid = ev.event_id or _event_id(ev)
    return {"twin": t.to_dict(), "event_id": eid, "input_hash": t.fingerprint()}


@_guard
def getFarmState(request: dict) -> dict:
    return _state(twin_from_dict(request["twin"]), _date(request["as_of"]))


@_guard
def getFarmAlerts(request: dict) -> dict:
    return {"as_of": request["as_of"], "alerts": _alerts(twin_from_dict(request["twin"]), _date(request["as_of"]))}


@_guard
def replayFarmTimeline(request: dict) -> dict:
    return _replay(twin_from_dict(request["twin"]), _date(request["from"]), _date(request["to"]), with_alerts=request.get("with_alerts", True))
