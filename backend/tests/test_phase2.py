from datetime import timedelta

from backend.detector import detect
from backend.main import calculate_data_quality
from backend.scoring import score
from backend.simulator import simulate


def test_multiple_events_are_serialized_and_deterministic():
    detected = detect(simulate("normal", 60, 42), 42)
    for column in ("threshold_candidate", "isolation_candidate", "combined_candidate", "candidate"):
        detected[column] = False
    detected.loc[10:14, "combined_candidate"] = True
    detected.loc[10:14, "candidate"] = True
    detected.loc[30:34, "combined_candidate"] = True
    detected.loc[30:34, "candidate"] = True

    _, primary, events = score(detected)
    _, repeated_primary, repeated_events = score(detected)

    assert len(events) == 2
    assert primary in events
    assert [item.event_id for item in events] == [item.event_id for item in repeated_events]
    assert primary.event_id == repeated_primary.event_id
    assert all(item.status == "resolved" for item in events)
    assert all(item.model_dump(mode="json") for item in events)


def test_data_quality_counts_actual_gaps_stale_values_and_missing_values():
    frame = simulate("normal", 60, 42)
    frame.loc[2, "timestamp"] = frame.loc[1, "timestamp"]
    frame.loc[3, "timestamp"] = frame.loc[1, "timestamp"] + timedelta(minutes=3)
    frame.loc[4, "battery_voltage"] = float("nan")

    quality = calculate_data_quality(frame)

    assert quality.timestamp_continuity is False
    assert quality.telemetry_gap_count == 1
    assert quality.stale_observation_count == 2
    assert quality.missing_value_count == 1
    assert quality.available_channels == 8

