"""Event replay: step a FarmTwin through time to show how state changes with each event (no real-time claims)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Optional

from .alerts import get_farm_alerts
from .twin import FarmTwin, evaluate_water_balance, get_farm_state, _planting_event


def replay_farm_timeline(twin: FarmTwin, start: date, end: date, *, with_alerts: bool = True) -> dict:
    """One frame per day from start..end. Each frame = state estimated AS OF that day (weather and events after the day are not used)."""
    if end < start:
        raise ValueError("end before start")
    frames = []
    d = start
    prev_state = None
    while d <= end:
        st = get_farm_state(twin, d)
        ws = st.get("water_state") or {}
        key = "depletion_mm" if ws.get("model") == "upland_root_zone" else "ponding_mm"
        today_events = [e.to_dict() for e in twin.events if e.date == d]
        wx = next((w for w in twin.weather if w.date == d), None)
        frame = {
            "date": d.isoformat(), "status": st["status"], "verdict": st["answer"]["verdict"],
            "stage": (st.get("crop") or {}).get("stage"), "dap": (st.get("crop") or {}).get("days_after_planting"),
            "water": None if not ws else {"model": ws["model"], key: ws[key], **({"raw_mm": ws["raw_mm"], "taw_mm": ws["taw_mm"]} if key == "depletion_mm" else {})},
            "events": today_events,
            "weather": None if wx is None else {"precip_mm": wx.precip_mm, "precip_source": wx.precip_source, "precip_type": wx.precip_type},
            "weather_lag_days": st["freshness"]["weather_lag_days"],
            "alerts": [{"kind": a["kind"], "class": a["class"]} for a in get_farm_alerts(twin, d)] if with_alerts else None,
        }
        if prev_state and ws and prev_state.get("model") == ws.get("model"):
            a, b = prev_state[key], ws[key]
            if a["low"] is not None and b["low"] is not None:
                frame["delta_mm"] = round(b["low"] - a["low"], 2)
        prev_state = ws or prev_state
        frames.append(frame)
        d += timedelta(days=1)
    return {"farm_id": twin.profile.farm_id, "from": start.isoformat(), "to": end.isoformat(), "frames": frames,
            "note": "replay of dated events over a weather series; not a live feed"}


def explain_event_effect(twin: FarmTwin, event_id: str, as_of: date) -> dict:
    """Counterfactual: the same twin with and without one event, so the dashboard can say what that irrigation changed."""
    ev = [e for e in twin.events if e.event_id == event_id]
    if not ev:
        raise KeyError(event_id)
    without = replace(twin, events=tuple(e for e in twin.events if e.event_id != event_id))
    a = evaluate_water_balance(twin, as_of)
    b = evaluate_water_balance(without, as_of)
    if a["status"] == "verification_needed" or b["status"] == "verification_needed":
        return {"event_id": event_id, "status": "verification_needed"}
    key = "depletion_mm" if a["water_state"]["model"] == "upland_root_zone" else "ponding_mm"
    return {"event_id": event_id, "as_of": as_of.isoformat(), "metric": key,
            "with_event": a["water_state"][key], "without_event": b["water_state"][key],
            "delta_low_mm": round(a["water_state"][key]["low"] - b["water_state"][key]["low"], 2)}
