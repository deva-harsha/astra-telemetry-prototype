import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .simulator import CHANNELS


WINDOW = 5
DEFAULT_CONTAMINATION = 0.06
DEFAULT_ISOLATION_THRESHOLD = -0.04


def rolling_features(frame: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    features: dict[str, pd.Series] = {}
    for channel in CHANNELS:
        values = frame[channel]
        rolling = values.rolling(window, min_periods=1)
        features[channel] = values
        features[f"{channel}_mean"] = rolling.mean()
        features[f"{channel}_std"] = rolling.std().fillna(0)
        features[f"{channel}_change"] = values.diff().fillna(0)
        features[f"{channel}_slope"] = (values - values.shift(window - 1)).fillna(0) / max(1, window - 1)
    return pd.DataFrame(features, index=frame.index).fillna(0)


def fit_isolation_forest(
    training_frames: list[pd.DataFrame],
    seed: int,
    window: int = WINDOW,
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = 100,
) -> IsolationForest:
    training = pd.concat(
        [rolling_features(frame, window) for frame in training_frames],
        ignore_index=True,
    )
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=seed,
        n_jobs=1,
    )
    return model.fit(training)


def detect(
    frame: pd.DataFrame,
    seed: int,
    model: IsolationForest | None = None,
    window: int = WINDOW,
    isolation_threshold: float = DEFAULT_ISOLATION_THRESHOLD,
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = 100,
    thermal_temperature_threshold: float = 31.0,
    payload_temperature_threshold: float = 33.0,
    battery_voltage_threshold: float = 26.5,
    battery_current_threshold: float = 3.0,
) -> pd.DataFrame:
    features = rolling_features(frame, window)
    if model is None:
        normal_end = int(len(frame) * 0.6)
        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=seed,
            n_jobs=1,
        ).fit(features.iloc[:normal_end])

    decision_score = model.decision_function(features)
    margins = -decision_score
    # The display anomaly index is not a calibrated probability.
    anomaly_score = np.clip(50 + 250 * margins, 0, 100)
    out = frame.copy()
    out["isolation_decision_score"] = decision_score
    out["anomaly_score"] = anomaly_score

    out["thermal_threshold"] = (out.battery_temperature > thermal_temperature_threshold) | (out.payload_temperature > payload_temperature_threshold)
    out["power_threshold"] = (out.battery_voltage < battery_voltage_threshold) | (out.battery_current > battery_current_threshold)
    out["threshold_breach"] = out.thermal_threshold | out.power_threshold
    out["thermal_trend"] = (
        features["battery_temperature_slope"] > 0.12
    ) & (features["payload_temperature_slope"] > 0.12)
    out["power_trend"] = (
        (features["battery_voltage_slope"] < -0.035)
        & (features["battery_current_slope"] > 0.025)
    )
    out["threshold_candidate"] = out.threshold_breach
    out["isolation_candidate"] = out.isolation_decision_score < isolation_threshold
    out["combined_candidate"] = out.threshold_candidate | (
        out.isolation_candidate & (out.thermal_trend | out.power_trend)
    )
    # Backward-compatible name used by live scoring.
    out["candidate"] = out.combined_candidate
    return out
