from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Scenario = Literal["normal", "thermal_fault", "power_fault"]
Severity = Literal["normal", "low", "medium", "high"]


class SimulationRequest(BaseModel):
    scenario: Scenario = "normal"
    points: int = Field(default=180, ge=60, le=1000)
    seed: int = 42


class TelemetryPoint(BaseModel):
    timestamp: datetime
    battery_voltage: float
    battery_current: float
    battery_temperature: float
    signal_strength: float
    attitude_error: float
    payload_temperature: float
    propulsion_pressure: float
    radiation_level: float
    anomaly_score: float
    is_anomaly: bool
    risk_score: float
    health_score: float
    severity: Severity


class Event(BaseModel):
    title: str
    severity: Severity
    affected_subsystem: str
    contributing_channels: list[str]
    event_start_time: datetime
    duration: int = Field(description="Number of one-minute observations in the event")
    explanation: str
    operator_review_message: str


class Metadata(BaseModel):
    scenario: Scenario
    points: int
    seed: int
    source: str = "Simulated telemetry"
    interval_seconds: int = 60
    score_note: str = "Risk and health scores are prototype heuristic indicators, not failure probabilities."
    units: dict[str, str]


class Metrics(BaseModel):
    processing_latency_ms: float
    detected_event_count: int
    maximum_anomaly_score: float
    risk_score: float
    health_score: float


class SimulationResponse(BaseModel):
    metadata: Metadata
    telemetry: list[TelemetryPoint]
    event: Event | None
    metrics: Metrics
