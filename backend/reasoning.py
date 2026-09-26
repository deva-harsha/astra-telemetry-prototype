"""Read-only explanations derived from the live detector's existing columns."""

from __future__ import annotations

from typing import Any

import pandas as pd


FINAL_LOGIC = (
    "combined candidate = threshold candidate OR (Isolation Forest candidate AND "
    "(thermal trend OR power trend)); confirmation requires 3 consecutive combined candidates"
)


def candidate_streaks(values: pd.Series) -> tuple[list[int], list[bool]]:
    streak = 0
    counts: list[int] = []
    resets: list[bool] = []
    for value in values.astype(bool):
        previous = streak
        streak = previous + 1 if value else 0
        counts.append(streak)
        resets.append(not value and previous > 0)
    return counts, resets


def _violations(row: Any) -> list[dict[str, Any]]:
    checks = (
        ("battery_temperature", float(row.battery_temperature), ">", float(row.battery_temperature_limit), bool(row.battery_temperature_limit_breach)),
        ("payload_temperature", float(row.payload_temperature), ">", float(row.payload_temperature_limit), bool(row.payload_temperature_limit_breach)),
        ("battery_voltage", float(row.battery_voltage), "<", float(row.battery_voltage_limit), bool(row.battery_voltage_limit_breach)),
        ("battery_current", float(row.battery_current), ">", float(row.battery_current_limit), bool(row.battery_current_limit_breach)),
    )
    return [
        {"channel": channel, "value": value, "operator": operator, "limit": limit}
        for channel, value, operator, limit, breached in checks
        if breached
    ]


def _trend_signals(row: Any) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    if bool(row.thermal_trend):
        signals.extend((
            {"channel": "battery_temperature", "direction": "rising"},
            {"channel": "payload_temperature", "direction": "rising"},
        ))
    if bool(row.power_trend):
        signals.extend((
            {"channel": "battery_voltage", "direction": "falling"},
            {"channel": "battery_current", "direction": "rising"},
        ))
    return signals


def reasoning_for_row(row: Any, observation_index: int, persistence: int = 3) -> dict[str, Any]:
    violations = _violations(row)
    trend_signals = _trend_signals(row)
    threshold_candidate = bool(row.threshold_candidate)
    isolation_candidate = bool(row.isolation_candidate)
    trend_supported = bool(row.thermal_trend or row.power_trend)
    combined_candidate = bool(row.combined_candidate)
    confirmed = bool(row.confirmed_combined_event)

    statements: list[str] = []
    if violations:
        statements.append("Configured operating limits were crossed by " + ", ".join(item["channel"] for item in violations) + ".")
    else:
        statements.append("No configured operating limit was crossed at this observation.")
    if isolation_candidate:
        statements.append("Isolation Forest marked the observation as unusual relative to the initial normal-training portion.")
    if trend_supported:
        statements.append("Related signal direction supported the candidate anomaly.")
    if confirmed:
        statements.append(f"The combined candidate persisted for the required {persistence} observations, so ASTRA confirmed an event for operator review.")
    elif combined_candidate:
        statements.append(f"The observation is a combined candidate but has not yet met the {persistence}-observation persistence requirement.")
    else:
        statements.append("The final hybrid candidate rule was not satisfied.")

    return {
        "observation_index": observation_index,
        "threshold": {
            "breach_count": len(violations),
            "channels": [item["channel"] for item in violations],
            "violations": violations,
            "state": "candidate" if threshold_candidate else "normal",
            "confirmed_by_persistence": bool(row.confirmed_threshold_event),
        },
        "isolation_forest": {
            "unusual": isolation_candidate,
            "anomaly_score": round(float(row.anomaly_score), 1),
            "decision_score": round(float(row.isolation_decision_score), 6),
            "candidate_threshold": float(row.isolation_candidate_threshold),
            "training_observations": int(row.isolation_training_observations),
            "initial_training_fraction": float(row.isolation_training_fraction),
            "model_state": "candidate" if isolation_candidate else "normal",
            "confirmed_by_persistence": bool(row.confirmed_model_event),
            "explanation": "The decision score is below the configured candidate threshold." if isolation_candidate else "The decision score is at or above the configured candidate threshold.",
        },
        "trend": {
            "corroborated": trend_supported,
            "signals": trend_signals,
            "window_observations": int(row.detector_window),
            "state": "supporting" if trend_supported else "absent",
        },
        "persistence": {
            "current_count": int(row.combined_candidate_streak),
            "required_count": persistence,
            "confirmed": confirmed,
            "confirmation_observation": observation_index if confirmed else None,
            "reset": bool(row.combined_candidate_reset),
        },
        "final_decision": {
            "candidate": combined_candidate,
            "confirmed": confirmed,
            "logic": FINAL_LOGIC,
        },
        "explanation": " ".join(statements),
    }
