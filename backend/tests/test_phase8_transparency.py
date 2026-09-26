import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)
BASELINE = json.loads((Path(__file__).parent / "fixtures" / "phase8_baseline.json").read_text(encoding="utf-8"))


def run(scenario: str) -> dict:
    response = client.post("/api/simulate", json={"scenario": scenario, "points": 180, "seed": 42})
    assert response.status_code == 200
    return response.json()


def test_original_event_scores_timing_and_ids_match_prefeature_snapshot():
    for scenario, expected in BASELINE.items():
        actual = run(scenario)
        assert actual["metadata"] == expected["metadata"]
        assert actual["metrics"] | {"processing_latency_ms": 0} == expected["metrics"] | {"processing_latency_ms": 0}
        assert [
            {key: point[key] for key in expected_point}
            for point, expected_point in zip(actual["telemetry"], expected["telemetry"], strict=True)
        ] == expected["telemetry"]
        assert [
            {key: event[key] for key in expected_event}
            for event, expected_event in zip(actual["events"], expected["events"], strict=True)
        ] == expected["events"]
        if expected["event"] is None:
            assert actual["event"] is None
        else:
            assert {key: actual["event"][key] for key in expected["event"]} == expected["event"]


def test_reasoning_is_derived_from_actual_threshold_model_and_persistence_state():
    data = run("power_fault")
    streak = 0
    for index, point in enumerate(data["telemetry"]):
        evidence = point["detector_reasoning"]
        expected_channels = []
        if point["battery_temperature"] > 31.0:
            expected_channels.append("battery_temperature")
        if point["payload_temperature"] > 33.0:
            expected_channels.append("payload_temperature")
        if point["battery_voltage"] < 26.5:
            expected_channels.append("battery_voltage")
        if point["battery_current"] > 3.0:
            expected_channels.append("battery_current")
        assert evidence["threshold"]["channels"] == expected_channels
        assert evidence["threshold"]["breach_count"] == len(expected_channels)
        assert evidence["isolation_forest"]["unusual"] == (
            evidence["isolation_forest"]["decision_score"] < evidence["isolation_forest"]["candidate_threshold"]
        )
        candidate = evidence["final_decision"]["candidate"]
        streak = streak + 1 if candidate else 0
        assert evidence["persistence"]["current_count"] == streak
        assert evidence["persistence"]["required_count"] == 3
        assert evidence["final_decision"]["confirmed"] == (streak >= 3)
        assert point["is_anomaly"] == evidence["final_decision"]["confirmed"]
        if index < 2:
            assert evidence["final_decision"]["confirmed"] is False


def test_event_reasoning_is_the_actual_confirmation_observation():
    data = run("thermal_fault")
    for event in data["events"]:
        reasoning = event["detector_reasoning"]
        point = data["telemetry"][reasoning["observation_index"]]
        assert point["timestamp"] == event["alert_confirmed_time"]
        assert reasoning == point["detector_reasoning"]
        assert reasoning["persistence"]["current_count"] == 3
        assert reasoning["final_decision"]["confirmed"] is True
        assert "root cause" not in reasoning["explanation"].lower()


def test_normal_stays_event_free_and_production_does_not_import_torch():
    data = run("normal")
    assert data["event"] is None
    assert data["events"] == []
    assert "torch" not in sys.modules


def test_visualisation_only_upload_has_no_detector_conclusions_or_accuracy_metrics():
    response = client.post(
        "/api/import/telemetry",
        content=b"timestamp,unknown_sensor\n2026-01-01T00:00:00Z,1\n2026-01-01T00:01:00Z,2\n",
        headers={"Content-Type": "text/csv", "X-ASTRA-Filename": "unknown.csv"},
    )
    payload = response.json()
    assert payload["compatibility"] == "visualisation_only"
    assert payload["event"] is None and payload["events"] == [] and payload["metrics"] is None
    encoded = json.dumps(payload).lower()
    for forbidden in ("precision", "recall", "accuracy", "false_positive", "false_negative", "detector_reasoning"):
        assert forbidden not in encoded
