import pandas as pd

from .schemas import Event


LIVE_DETECTOR_METHOD = "Live hybrid: fixed operating thresholds plus Isolation Forest with trend corroboration"


def persistence_mask(values: pd.Series, length: int = 3) -> pd.Series:
    streak = 0
    confirmed: list[bool] = []
    for value in values.astype(bool):
        streak = streak + 1 if value else 0
        confirmed.append(streak >= length)
    return pd.Series(confirmed, index=values.index, dtype=bool)


def _subsystem(row: pd.Series) -> str:
    thermal = bool(row.thermal_threshold or row.thermal_trend)
    power = bool(row.power_threshold or row.power_trend)
    if power and (not thermal or row.battery_voltage < 26.5):
        return "Power"
    if thermal:
        return "Thermal"
    return "Telemetry"


def _event_description(subsystem: str) -> tuple[list[str], str, str]:
    if subsystem == "Power":
        return (
            ["battery_voltage", "battery_current", "battery_temperature"],
            "Battery voltage is falling while battery current and temperature are increasing. The unusual pattern persisted across multiple observations.",
            "Persistent power telemetry anomaly",
        )
    if subsystem == "Thermal":
        return (
            ["battery_temperature", "payload_temperature"],
            "Battery and payload temperatures are increasing together. The unusual pattern persisted across multiple observations.",
            "Persistent thermal telemetry anomaly",
        )
    return (
        [],
        "Multiple observations show an unusual telemetry pattern that requires operator review.",
        "Persistent telemetry anomaly",
    )


def score(frame: pd.DataFrame, persistence: int = 3) -> tuple[pd.DataFrame, Event | None, list[Event]]:
    out = frame.copy()
    out["confirmed_threshold_event"] = persistence_mask(out["threshold_candidate"], persistence)
    out["confirmed_model_event"] = persistence_mask(out["isolation_candidate"], persistence)
    out["confirmed_combined_event"] = persistence_mask(out["combined_candidate"], persistence)
    persistent = out["confirmed_combined_event"].tolist()

    risks: list[float] = []
    severities: list[str] = []
    for index, row in enumerate(out.itertuples()):
        confirmed = bool(persistent[index])
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

    out["risk_score"] = risks
    out["health_score"] = [round(100 - value, 1) for value in risks]
    out["severity"] = severities
    out["is_anomaly"] = persistent

    starts = [index for index, value in enumerate(persistent) if value and (index == 0 or not persistent[index - 1])]
    if not starts:
        return out, None, []

    episodes: list[tuple[int, int, int]] = []
    for confirmed_start in starts:
        onset = max(0, confirmed_start - persistence + 1)
        end = confirmed_start
        while end + 1 < len(out) and bool(out.iloc[end + 1].combined_candidate):
            end += 1
        episodes.append((onset, end, confirmed_start))

    events: list[Event] = []
    for sequence, (onset, end, confirmed_start) in enumerate(episodes, start=1):
        segment = out.iloc[onset:end + 1]
        peak = segment.loc[segment.risk_score.idxmax()]
        subsystem = _subsystem(peak)
        channels, explanation, title = _event_description(subsystem)
        start_time = out.iloc[onset].timestamp
        is_active = end == len(out) - 1 and bool(out.iloc[end].combined_candidate)
        identifier = f"ASTRA-{start_time.strftime('%Y%m%dT%H%M%SZ')}-{subsystem.lower()}-{sequence:02d}"
        events.append(Event(
            event_id=identifier,
            title=title,
            severity=str(peak.severity),
            affected_subsystem=subsystem,
            status="active" if is_active else "resolved",
            contributing_channels=channels,
            event_start_time=start_time,
            event_end_time=None if is_active else out.iloc[end].timestamp,
            alert_confirmed_time=out.iloc[confirmed_start].timestamp,
            duration=end - onset + 1,
            explanation=explanation,
            supporting_evidence=explanation,
            detector_method=LIVE_DETECTOR_METHOD,
            threshold_status="confirmed" if bool(segment.confirmed_threshold_event.any()) else "not_confirmed",
            isolation_forest_status="confirmed" if bool(segment.confirmed_model_event.any()) else "not_confirmed",
            persistence_count=persistence,
            final_decision="persistent event confirmed",
            operator_review_message="Review the contributing telemetry and spacecraft context before taking action. This prototype does not confirm a root cause.",
        ))

    severity_rank = {"normal": 0, "low": 1, "medium": 2, "high": 3}
    primary = max(events, key=lambda item: (severity_rank[item.severity], item.duration))
    return out, primary, events
