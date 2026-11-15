"""Deterministic SYNTHETIC weather for demos and tests. NOT NASA DATA.

Seasonal shape is roughly sub-tropical monsoon (hot pre-monsoon, wet Jun-Sep, cool dry winter) so the model has
something plausible to run on, but the numbers are invented. Rows are tagged met_source/precip_source='SYNTHETIC_FIXTURE'
and type 'hypothetical_scenario' so the engine will never present a recommendation built on them as a real answer.
Replace with EarthSync NASA POWER rows (see power_adapter.parse_power_json)."""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from .models import DailyWeather


def synthetic_monsoon_weather(start: date, end: date, seed: int = 7, *, source: str = "SYNTHETIC_FIXTURE",
                              dtype: str = "hypothetical_scenario") -> list[DailyWeather]:
    rng = random.Random(seed)
    rows = []
    d = start
    while d <= end:
        doy = d.timetuple().tm_yday
        # temperature: peak ~ day 130 (May), trough ~ day 15
        t_mean = 25.5 + 5.5 * math.sin(2 * math.pi * (doy - 105) / 365)
        tmax = t_mean + 5.0 + rng.uniform(-1.2, 1.2)
        tmin = t_mean - 5.0 + rng.uniform(-1.0, 1.0)
        monsoon = max(0.0, math.sin(math.pi * (doy - 150) / 120)) if 150 <= doy <= 270 else 0.0
        rh = 55 + 30 * monsoon + rng.uniform(-6, 6) + (5 if 330 < doy or doy < 40 else 0)
        wet = rng.random() < (0.12 + 0.55 * monsoon)
        rain = round(rng.expovariate(1 / (6 + 18 * monsoon)), 1) if wet else 0.0
        rs = 18.0 + 5.0 * math.sin(2 * math.pi * (doy - 80) / 365) - 9.0 * monsoon * rng.uniform(0.3, 1.0) - (4.0 if rain > 5 else 0)
        rows.append(DailyWeather(date=d, tmax_c=round(tmax, 1), tmin_c=round(tmin, 1), rh_mean_pct=round(min(max(rh, 25), 98), 0),
                                 wind_2m_ms=round(1.2 + 0.8 * rng.random() + 0.6 * monsoon, 2), solar_mj_m2_day=round(max(rs, 5.0), 1),
                                 precip_mm=rain, met_source=source, met_type=dtype, precip_source=source, precip_type=dtype,
                                 ingested_at="synthetic"))
        d += timedelta(days=1)
    return rows
