import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .simulator import CHANNELS


WINDOW = 5


def rolling_features(frame: pd.DataFrame) -> pd.DataFrame:
    features: dict[str, pd.Series] = {}
    for channel in CHANNELS:
        values = frame[channel]
        rolling = values.rolling(WINDOW, min_periods=1)
        features[channel] = values
        features[f"{channel}_mean"] = rolling.mean()
        features[f"{channel}_std"] = rolling.std().fillna(0)
        features[f"{channel}_change"] = values.diff().fillna(0)
        features[f"{channel}_slope"] = (values - values.shift(WINDOW - 1)).fillna(0) / (WINDOW - 1)
    return pd.DataFrame(features, index=frame.index).fillna(0)


def detect(frame: pd.DataFrame, seed: int) -> pd.DataFrame:
    features = rolling_features(frame)
    normal_end = int(len(frame) * 0.6)
    model = IsolationForest(n_estimators=100, contamination=0.06, random_state=seed, n_jobs=1)
    model.fit(features.iloc[:normal_end])
    margins = -model.decision_function(features)
    # The score is a display index, not a calibrated probability.
    anomaly_score = np.clip(50 + 250 * margins, 0, 100)
    out = frame.copy()
    out["anomaly_score"] = anomaly_score

    out["thermal_threshold"] = (out.battery_temperature > 31) | (out.payload_temperature > 33)
    out["power_threshold"] = (out.battery_voltage < 26.5) | (out.battery_current > 3.0)
    out["threshold_breach"] = out.thermal_threshold | out.power_threshold
    out["thermal_trend"] = (
        features["battery_temperature_slope"] > 0.12
    ) & (features["payload_temperature_slope"] > 0.12)
    out["power_trend"] = (
        (features["battery_voltage_slope"] < -0.035)
        & (features["battery_current_slope"] > 0.025)
    )
    out["candidate"] = out.threshold_breach | (
        (out.anomaly_score >= 60) & (out.thermal_trend | out.power_trend)
    )
    return out
