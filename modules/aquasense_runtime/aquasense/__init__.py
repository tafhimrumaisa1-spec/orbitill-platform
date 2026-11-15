"""AquaSense FieldTwin: water physics + farm state + AgriPulse alerts (ORBITILL RootShift, Agent 06)."""
from .models import (Observation, DailyWeather, SoilProfile, FarmConstraints, FarmProfile, FarmEvent, MODEL_VERSION)
from .twin import FarmTwin, apply_farm_event, evaluate_water_balance, get_farm_state
from .alerts import get_farm_alerts
from .replay import replay_farm_timeline, explain_event_effect
from .season import estimate_crop_et, estimate_season_irrigation
from .contract import (evaluateWaterBalance, estimateCropET, applyFarmEvent, getFarmState, getFarmAlerts,
                       replayFarmTimeline, answerDoINeedWater)

__all__ = [n for n in dir() if not n.startswith("_")]
__version__ = "0.1.0"
