from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Scenario = Literal["normal", "thermal_fault", "power_fault"]
Severity = Literal["normal", "low", "medium", "high"]
EventStatus = Literal["active", "resolved"]


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
    fault_active: bool = False
    fault_type: Scenario | None = None
    injected_subsystem: str | None = None
    fault_start_index: int | None = None
    fault_start_timestamp: datetime | None = None
    ground_truth_event_id: str | None = None


class Event(BaseModel):
    event_id: str
    title: str
    severity: Severity
    affected_subsystem: str
    status: EventStatus
    contributing_channels: list[str]
    event_start_time: datetime
    event_end_time: datetime | None = None
    alert_confirmed_time: datetime | None = None
    duration: int = Field(description="Number of one-minute observations in the event")
    explanation: str
    supporting_evidence: str
    detector_method: str
    threshold_status: Literal["confirmed", "not_confirmed"]
    isolation_forest_status: Literal["confirmed", "not_confirmed"]
    persistence_count: int
    final_decision: str
    operator_review_message: str


class DataQuality(BaseModel):
    timestamp_continuity: bool
    missing_value_count: int
    telemetry_gap_count: int
    stale_observation_count: int
    available_channels: int
    data_source: str


class Metadata(BaseModel):
    scenario: Scenario
    points: int
    seed: int
    source: str = "Simulated telemetry"
    interval_seconds: int = 60
    score_note: str = "Risk and health scores are prototype heuristic indicators, not failure probabilities."
    units: dict[str, str]
    fault_start_index: int | None = None
    fault_start_timestamp: datetime | None = None


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
    events: list[Event]
    data_quality: DataQuality
    metrics: Metrics
