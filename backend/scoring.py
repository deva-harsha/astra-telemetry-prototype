import pandas as pd

from .schemas import Event


def _subsystem(row: pd.Series) -> str:
    thermal = bool(row.thermal_threshold or row.thermal_trend)
    power = bool(row.power_threshold or row.power_trend)
    if power and (not thermal or row.battery_voltage < 26.5):
        return "Power"
    if thermal:
        return "Thermal"
    return "Telemetry"


def score(frame: pd.DataFrame) -> tuple[pd.DataFrame, Event | None, int]:
    out = frame.copy()
    risks: list[float] = []
    severities: list[str] = []
    persistent: list[bool] = []
    streak = 0
    for row in out.itertuples():
        streak = streak + 1 if row.candidate else 0
        confirmed = streak >= 3
        threshold_weight = 0
        if row.thermal_threshold:
            threshold_weight += 22
        if row.power_threshold:
            threshold_weight += 25
        if row.battery_temperature > 35 or row.payload_temperature > 38:
            threshold_weight += 13
        if row.battery_voltage < 25.5:
            threshold_weight += 13
        trend_weight = (10 if row.thermal_trend else 0) + (10 if row.power_trend else 0)
        model_weight = max(0, row.anomaly_score - 50) * 0.35
        risk = round(min(100, max(0, threshold_weight + trend_weight + model_weight + (20 if confirmed else 0))), 1)
        if not confirmed:
            severity = "low" if row.candidate else "normal"
        elif risk >= 70:
            severity = "high"
        elif risk >= 40:
            severity = "medium"
        else:
            severity = "low"
        risks.append(risk)
        severities.append(severity)
        persistent.append(confirmed)
    out["risk_score"] = risks
    out["health_score"] = [round(100 - value, 1) for value in risks]
    out["severity"] = severities
    out["is_anomaly"] = persistent

    # Count contiguous confirmed episodes. The event begins at the first candidate
    # in the confirming streak, so the UI can reveal it at confirmation time.
    starts = [i for i, value in enumerate(persistent) if value and (i == 0 or not persistent[i - 1])]
    if not starts:
        return out, None, 0
    episodes: list[tuple[int, int]] = []
    for confirmed_start in starts:
        onset = confirmed_start - 2
        end = confirmed_start
        while end + 1 < len(out) and bool(out.iloc[end + 1].candidate):
            end += 1
        episodes.append((onset, end))
    onset, end = max(episodes, key=lambda pair: (out.iloc[pair[0]:pair[1] + 1].risk_score.max(), pair[1] - pair[0]))
    segment = out.iloc[onset:end + 1]
    peak = segment.loc[segment.risk_score.idxmax()]
    subsystem = _subsystem(peak)
    if subsystem == "Power":
        channels = ["battery_voltage", "battery_current", "battery_temperature"]
        explanation = "Battery voltage is falling while battery current and temperature are increasing. The unusual pattern persisted across multiple observations."
        title = "Persistent power telemetry anomaly"
    elif subsystem == "Thermal":
        channels = ["battery_temperature", "payload_temperature"]
        explanation = "Battery and payload temperatures are increasing together. The unusual pattern persisted across multiple observations."
        title = "Persistent thermal telemetry anomaly"
    else:
        channels = []
        explanation = "Multiple observations show an unusual telemetry pattern that requires operator review."
        title = "Persistent telemetry anomaly"
    severity = str(peak.severity)
    event = Event(
        title=title,
        severity=severity,
        affected_subsystem=subsystem,
        contributing_channels=channels,
        event_start_time=out.iloc[onset].timestamp,
        duration=end - onset + 1,
        explanation=explanation,
        operator_review_message="Review the contributing telemetry and spacecraft context before taking action. This prototype does not confirm a root cause.",
    )
    return out, event, len(episodes)
