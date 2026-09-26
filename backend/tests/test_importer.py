from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.importer import (
    ASTRA_PROFILE,
    ImportValidationError,
    MAX_FILE_BYTES,
    MAX_ROWS,
    process_recorded_csv,
)
from backend.main import app
from backend.simulator import CHANNELS, simulate


client = TestClient(app)


def simulator_csv(scenario: str = "normal", points: int = 180) -> bytes:
    frame = simulate(scenario, points, 42)[["timestamp", *CHANNELS]].copy()
    frame.insert(1, "mission_id", "ASTRA-DEMO")
    return frame.to_csv(index=False).encode()


def analyse(content: bytes, **kwargs):
    return process_recorded_csv(
        content,
        filename=kwargs.pop("filename", "telemetry.csv"),
        timestamp_column=kwargs.pop("timestamp_column", "timestamp"),
        mission_column=kwargs.pop("mission_column", "mission_id"),
        mapping=kwargs.pop("mapping", {channel: channel for channel in CHANNELS}),
        units_confirmed=kwargs.pop("units_confirmed", True),
        **kwargs,
    )


def test_valid_compatible_normal_csv_uses_existing_response_shape():
    result = analyse(simulator_csv())
    assert result["compatibility"] == "compatible"
    assert result["profile"]["profile_id"] == "astra-sim-v1"
    assert len(result["telemetry"]) == 180
    assert result["events"] == []
    assert result["metrics"]["detected_event_count"] == 0
    assert len(result["preview"]) == 10


def test_compatible_fault_demo_reproduces_persistent_event():
    result = analyse(simulator_csv("power_fault"))
    assert result["compatibility"] == "compatible"
    assert any(event["affected_subsystem"] == "Power" for event in result["events"])


def test_visualisation_only_csv_never_creates_detector_conclusions():
    result = process_recorded_csv(
        b"timestamp,unknown_sensor\n2026-01-01T00:00:00Z,1\n2026-01-01T00:01:00Z,2\n",
        filename="unknown.csv",
        timestamp_column="timestamp",
    )
    assert result["compatibility"] == "visualisation_only"
    assert result["events"] == []
    assert result["metrics"] is None
    assert result["visualization_channels"] == ["unknown_sensor"]


def test_invalid_timestamps_are_reported_as_invalid():
    result = process_recorded_csv(
        b"timestamp,value\nnot-a-time,1\n",
        filename="bad.csv",
        timestamp_column="timestamp",
    )
    assert result["compatibility"] == "invalid"
    assert "could not be interpreted" in result["validation"]["errors"][0]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "empty_file"),
        (b"timestamp,value,value\n2026-01-01,1,2\n", "duplicate_headers"),
        (b"timestamp,label\n2026-01-01,hello\n", "no_numeric_channels"),
    ],
)
def test_invalid_csv_inputs_return_specific_errors(content: bytes, code: str):
    with pytest.raises(ImportValidationError) as error:
        process_recorded_csv(content, filename="test.csv", timestamp_column="timestamp")
    assert error.value.code == code


def test_oversized_file_and_excessive_rows_are_rejected():
    with pytest.raises(ImportValidationError) as size_error:
        process_recorded_csv(b"x" * (MAX_FILE_BYTES + 1), filename="large.csv")
    assert size_error.value.code == "file_too_large"

    rows = ["timestamp,value"] + [f"2026-01-01T00:00:00Z,{index}" for index in range(MAX_ROWS + 1)]
    with pytest.raises(ImportValidationError) as row_error:
        process_recorded_csv("\n".join(rows).encode(), filename="rows.csv", timestamp_column="timestamp")
    assert row_error.value.code == "too_many_rows"


def test_missing_channels_and_units_prevent_detector_compatibility():
    content = b"timestamp,mission_id,battery_voltage\n2026-01-01T00:00:00Z,X,28\n2026-01-01T00:01:00Z,X,28.1\n"
    result = process_recorded_csv(
        content,
        filename="partial.csv",
        timestamp_column="timestamp",
        mission_column="mission_id",
        mapping={"battery_voltage": "battery_voltage"},
        units_confirmed=False,
    )
    assert result["compatibility"] == "visualisation_only"
    assert any("requires mappings" in warning for warning in result["validation"]["warnings"])
    assert any("units" in warning.lower() for warning in result["validation"]["warnings"])


def test_quality_reports_missing_duplicate_out_of_order_and_constant_values():
    content = (
        b"timestamp,a,b\n"
        b"2026-01-01T00:01:00Z,1,\n"
        b"2026-01-01T00:01:00Z,1,2\n"
        b"2026-01-01T00:00:00Z,1,3\n"
    )
    result = process_recorded_csv(content, filename="quality.csv", timestamp_column="timestamp")
    quality = result["data_quality"]
    assert quality["missing_value_count"] == 1
    assert quality["duplicate_timestamp_count"] == 1
    assert quality["out_of_order_timestamp_count"] == 1
    assert "a" in quality["constant_channels"]


def test_non_numeric_and_formula_like_cells_are_never_executed():
    content = (
        b"timestamp,value\n"
        b"2026-01-01T00:00:00Z,1\n"
        b"2026-01-01T00:01:00Z,hello\n"
        b"2026-01-01T00:02:00Z,=2+2\n"
    )
    result = process_recorded_csv(content, filename="formula.csv", timestamp_column="timestamp")
    assert result["compatibility"] == "visualisation_only"
    assert any("non-numeric" in warning for warning in result["validation"]["warnings"])
    assert any("Formula-like" in warning for warning in result["validation"]["warnings"])
    assert result["preview"][2]["value"] == "=2+2"


def test_filename_is_sanitized_and_never_used_as_a_path():
    result = process_recorded_csv(
        b"timestamp,value\n2026-01-01T00:00:00Z,1\n2026-01-01T00:01:00Z,2\n",
        filename="../../<script>alert(1)</script>.csv",
        timestamp_column="timestamp",
    )
    safe_name = result["import_metadata"]["sanitized_filename"]
    assert safe_name == "script_.csv"
    assert ".." not in safe_name
    assert "/" not in safe_name and "\\" not in safe_name and "<" not in safe_name


def test_profile_contract_is_explicit_and_detector_compatible():
    assert ASTRA_PROFILE["canonical_channels"] == list(CHANNELS)
    assert ASTRA_PROFILE["required_channels"] == list(CHANNELS)
    assert ASTRA_PROFILE["detector_compatible"] is True
    assert "certification" in ASTRA_PROFILE["contract_note"]


def test_import_api_accepts_csv_and_rejects_non_csv_or_large_content_length():
    content = simulator_csv()
    headers = {
        "Content-Type": "text/csv",
        "X-ASTRA-Filename": "normal.csv",
        "X-ASTRA-Timestamp-Column": "timestamp",
        "X-ASTRA-Mission-Column": "mission_id",
        "X-ASTRA-Mapping": json.dumps({channel: channel for channel in CHANNELS}),
        "X-ASTRA-Units-Confirmed": "true",
    }
    response = client.post("/api/import/telemetry", content=content, headers=headers)
    assert response.status_code == 200
    assert response.json()["compatibility"] == "compatible"
    assert client.post("/api/import/telemetry", content=b"{}", headers={"Content-Type": "application/json"}).status_code == 415

    oversized = client.post(
        "/api/import/telemetry",
        content=b"x",
        headers={"Content-Type": "text/csv", "Content-Length": str(MAX_FILE_BYTES + 1)},
    )
    assert oversized.status_code == 413


def test_profile_sampling_interval_and_non_finite_values_disable_analysis():
    fast = simulate("normal", 12, 42)[["timestamp", *CHANNELS]].copy()
    fast["timestamp"] = pd.date_range("2026-01-01", periods=len(fast), freq="1s", tz="UTC")
    fast.insert(1, "mission_id", "FAST")
    result = analyse(fast.to_csv(index=False).encode())
    assert result["compatibility"] == "visualisation_only"
    assert any("60-second sampling interval" in warning for warning in result["validation"]["warnings"])

    content = b"timestamp,value\n2026-01-01T00:00:00Z,1\n2026-01-01T00:01:00Z,inf\n"
    result = process_recorded_csv(content, filename="nonfinite.csv", timestamp_column="timestamp")
    assert result["compatibility"] == "visualisation_only"
    assert result["telemetry"][1]["value"] is None


@pytest.mark.parametrize(
    ("filename", "expected_subsystem"),
    [
        ("astra-normal-demo.csv", None),
        ("astra-power-fault-demo.csv", "Power"),
    ],
)
def test_bundled_demonstration_csv_files_replay_consistently(filename: str, expected_subsystem: str | None):
    content = (Path("frontend/public/examples") / filename).read_bytes()
    result = analyse(content, filename=filename)
    assert result["compatibility"] == "compatible"
    assert len(result["telemetry"]) == 180
    if expected_subsystem is None:
        assert result["events"] == []
    else:
        assert any(event["affected_subsystem"] == expected_subsystem for event in result["events"])



@pytest.mark.parametrize("content", [
    b"timestamp,value\n2026-01-01,1,2\n",
    (",".join("c" + str(i) for i in range(65)) + "\n").encode(),
])
def test_malformed_or_excessively_wide_csv_is_rejected(content):
    with pytest.raises(ImportValidationError):
        process_recorded_csv(content, filename="bad.csv")


def test_non_csv_filename_is_rejected_by_backend():
    with pytest.raises(ImportValidationError) as error:
        analyse(simulator_csv(), filename="data.txt")
    assert error.value.code == "csv_required"


def test_irregular_sampling_is_not_accepted_from_median_alone():
    frame = simulate("normal", 12, 42)[["timestamp", *CHANNELS]].copy()
    frame.loc[6, "timestamp"] += pd.Timedelta(seconds=10)
    result = analyse(frame.to_csv(index=False).encode())
    assert result["compatibility"] == "visualisation_only"
    assert result["metrics"] is None


def test_explicit_empty_mapping_does_not_silently_restore_canonical_channels():
    result = analyse(simulator_csv(), mapping={})
    assert result["compatibility"] == "visualisation_only"
    assert result["mapping"] == {}
    assert result["metrics"] is None
