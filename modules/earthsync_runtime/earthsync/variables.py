"""Registry of provider variables we understand, with canonical units, native
grid and plausibility bounds used for per-variable quality flags."""
from __future__ import annotations

from dataclasses import dataclass

from . import gridinfo as G


@dataclass(frozen=True)
class VarSpec:
    provider_var: str
    variable: str            # scientific name used across ORBITILL
    dimension: str           # key into units.CANON
    grid: G.GridSpec
    lo: float                # plausibility bounds in canonical units
    hi: float
    process: str             # MeasurementProcess
    note: str = ""


MET, SOLAR = G.MERRA2, G.CERES_1DEG

POWER_VARS: dict[str, VarSpec] = {v.provider_var: v for v in [
    VarSpec("T2M", "air_temperature_2m_mean", "temperature", MET, -70, 60, "reanalysis_blend",
            "Daily mean 2 m air temperature; MERRA-2 based; not a station reading."),
    VarSpec("T2M_MAX", "air_temperature_2m_max", "temperature", MET, -70, 65, "reanalysis_blend",
            "Daily maximum of hourly gridded 2 m temperature; grid-cell mean, so it can differ from station Tmax."),
    VarSpec("T2M_MIN", "air_temperature_2m_min", "temperature", MET, -80, 55, "reanalysis_blend",
            "Daily minimum of hourly gridded 2 m temperature."),
    VarSpec("T2MDEW", "dew_point_2m_mean", "temperature", MET, -90, 40, "reanalysis_blend"),
    VarSpec("PRECTOTCORR", "precipitation_corrected", "precip_depth", MET, 0, 1500, "reanalysis_blend",
            "Bias-corrected MERRA-2 precipitation; observation-corrected reanalysis, not independent ground truth."),
    VarSpec("ALLSKY_SFC_SW_DWN", "shortwave_downward_allsky", "irradiance_daily", SOLAR, 0, 45, "satellite_model_blend",
            "All-sky surface shortwave downward irradiance (CERES-based); 1x1 deg."),
    VarSpec("RH2M", "relative_humidity_2m", "rh", MET, 0, 100.5, "reanalysis_blend"),
    VarSpec("WS2M", "wind_speed_2m", "wind", MET, 0, 100, "reanalysis_blend"),
    VarSpec("PS", "surface_pressure", "pressure", MET, 30, 110, "reanalysis_blend"),
]}

# Parameter requested for POWER-hosted IMERG v7B (integrated 2025-03-04 per POWER release guide).
# The exact parameter code could NOT be verified in-session (docs host blocked); the adapter
# treats a 422 from POWER as a typed ``parameter_rejected`` result instead of guessing.
POWER_IMERG_PARAM_CANDIDATES = ("IMERG_PRECTOT",)
