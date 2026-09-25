import json

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def run(scenario: str):
    response = client.post("/api/simulate", json={"scenario": scenario, "points": 180, "seed": 42})
    assert response.status_code == 200
    return response.json()


def test_health_and_scenarios():
    assert client.get("/api/health").json()["status"] == "ok"
    ids = [item["id"] for item in client.get("/api/scenarios").json()]
    assert ids == ["normal", "thermal_fault", "power_fault"]


def test_normal_returns_telemetry_without_high_risk_event():
    data = run("normal")
    assert len(data["telemetry"]) == 180
    assert data["event"] is None or data["event"]["severity"] != "high"
    assert data["metrics"]["detected_event_count"] == 0


def test_thermal_fault_produces_thermal_event():
    data = run("thermal_fault")
    assert data["event"]["affected_subsystem"] == "Thermal"
    assert "battery_temperature" in data["event"]["contributing_channels"]
    assert data["event"]["duration"] >= 3


def test_power_fault_produces_power_event():
    data = run("power_fault")
    assert data["event"]["affected_subsystem"] == "Power"
    assert "battery_voltage" in data["event"]["contributing_channels"]
    assert data["event"]["duration"] >= 3


def test_scores_bounded_and_json_valid():
    for scenario in ("normal", "thermal_fault", "power_fault"):
        response = client.post("/api/simulate", json={"scenario": scenario, "points": 180, "seed": 42})
        data = json.loads(response.text)
        for point in data["telemetry"]:
            assert 0 <= point["risk_score"] <= 100
            assert 0 <= point["health_score"] <= 100
        assert 0 <= data["metrics"]["risk_score"] <= 100
        assert 0 <= data["metrics"]["health_score"] <= 100


def test_seed_repeats_telemetry():
    first = run("thermal_fault")
    second = run("thermal_fault")
    assert first["telemetry"] == second["telemetry"]


def test_cors_restricted_to_local_vite():
    allowed = client.options("/api/simulate", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    denied = client.options("/api/simulate", headers={"Origin": "http://example.com", "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_api_returns_explicit_ground_truth_without_replacing_detector_decision():
    thermal = run("thermal_fault")
    onset = thermal["metadata"]["fault_start_index"]
    assert onset == 108
    assert thermal["metadata"]["fault_start_timestamp"] == thermal["telemetry"][onset]["timestamp"]
    assert thermal["telemetry"][onset]["fault_active"] is True
    assert thermal["telemetry"][onset]["ground_truth_event_id"] == "thermal_fault-1"
    assert isinstance(thermal["telemetry"][onset]["is_anomaly"], bool)
    assert thermal["event"]["alert_confirmed_time"] is not None


def test_event_field_is_backward_compatible_with_events_array():
    data = run("thermal_fault")
    assert data["events"]
    assert data["event"] in data["events"]
    assert data["metrics"]["detected_event_count"] == len(data["events"])


def test_normal_scenario_has_empty_events_array():
    data = run("normal")
    assert data["events"] == []
    assert data["event"] is None


def test_event_identifiers_are_stable_and_fields_are_json_safe():
    first = run("power_fault")
    second = run("power_fault")
    assert [event["event_id"] for event in first["events"]] == [event["event_id"] for event in second["events"]]
    event = first["events"][0]
    assert event["detector_method"].startswith("Live hybrid")
    assert event["persistence_count"] == 3
    assert event["threshold_status"] in {"confirmed", "not_confirmed"}
    assert event["isolation_forest_status"] in {"confirmed", "not_confirmed"}
    json.dumps(event)


def test_simulator_data_quality_is_calculated_from_response_data():
    quality = run("normal")["data_quality"]
    assert quality == {
        "timestamp_continuity": True,
        "missing_value_count": 0,
        "telemetry_gap_count": 0,
        "stale_observation_count": 0,
        "available_channels": 8,
        "data_source": "ASTRA deterministic simulator",
    }
