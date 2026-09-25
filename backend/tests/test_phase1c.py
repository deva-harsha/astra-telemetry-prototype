import copy
import json

import numpy as np
import pytest

from backend.evaluation.metrics import calculate_metrics, detection_delays
from backend.evaluation.phase1c import (
    BASE_CONFIG,
    _hash_config,
    _json_safe,
    macro_average,
    select_holdout_channels,
    verify_frozen_config,
)
from backend.evaluation.preprocessing import RobustFeatureScaler, chronological_split


def test_chronological_split_has_no_overlap():
    values = np.arange(20.0).reshape(10, 2)
    fit, validation = chronological_split(values, 0.7)
    assert fit[:, 0].tolist() == [0, 2, 4, 6, 8, 10, 12]
    assert validation[:, 0].tolist() == [14, 16, 18]
    assert not set(map(tuple, fit)) & set(map(tuple, validation))


def test_scaler_is_fitted_only_on_fit_section():
    fit = np.arange(20.0).reshape(10, 2)
    scaler = RobustFeatureScaler("raw", window=3).fit(fit)
    original_center = scaler.center_.copy()
    extreme_validation = np.full((4, 2), 1_000_000.0)
    transformed = scaler.transform(extreme_validation, fit[-2:])
    assert np.array_equal(scaler.center_, original_center)
    assert transformed[:, 0].min() > 1000


def test_missing_and_constant_features_are_handled():
    values = np.ones((12, 2))
    values[8, 0] = np.nan
    scaler = RobustFeatureScaler("combined", window=4).fit(values)
    transformed = scaler.transform(values)
    assert np.isfinite(transformed).all()
    assert "raw" not in scaler.retained_columns
    assert "missing" in scaler.retained_columns


def test_holdout_selection_is_deterministic_and_excludes_development(monkeypatch, tmp_path):
    channels = {
        "SMAP": ["A-1", "A-2", "A-3"] + [f"S-{i}" for i in range(20)],
        "MSL": ["C-1", "C-2", "D-14"] + [f"M-{i}" for i in range(20)],
    }
    monkeypatch.setattr("backend.evaluation.phase1c.available_channels", lambda root, mission: channels[mission])
    first = select_holdout_channels(tmp_path)
    second = select_holdout_channels(tmp_path)
    assert first == second
    assert len(first["SMAP"]) == len(first["MSL"]) == 10
    assert not {"A-1", "A-2", "A-3"} & set(first["SMAP"])
    assert not {"C-1", "C-2", "D-14"} & set(first["MSL"])


def test_frozen_configuration_hash_detects_changes():
    config = {**BASE_CONFIG, "frozen": True}
    config["configuration_sha256"] = _hash_config(config)
    verify_frozen_config(config)
    tampered = copy.deepcopy(config)
    tampered["rolling_window"] = 999
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_frozen_config(tampered)


def test_micro_and_macro_metrics_are_distinct_and_valid():
    truth_a = np.array([False, True, True])
    prediction_a = np.array([False, True, False])
    truth_b = np.array([False] * 7 + [True] * 3)
    prediction_b = np.array([False] * 10)
    micro = calculate_metrics([truth_a, truth_b], [prediction_a, prediction_b])
    per_run = [
        calculate_metrics([truth_a], [prediction_a]),
        calculate_metrics([truth_b], [prediction_b]),
    ]
    macro = macro_average(per_run, ("point_f1", "event_recall"))
    assert micro["point_f1"] != macro["point_f1"]
    assert macro["event_recall"] == 0.5


def test_event_matching_never_reports_negative_delay():
    truth = np.array([False, False, True, True])
    prediction = np.array([False, True, True, False])
    metrics = calculate_metrics([truth], [prediction], tolerance=1)
    assert metrics["mean_detection_delay_observations"] == 0.0
    assert detection_delays([truth], [prediction], tolerance=1) == [0]


def test_json_safe_outputs_are_serializable():
    payload = _json_safe({"integer": np.int64(3), "float": np.float64(1.5), "nan": np.float64(np.nan), "array": np.array([1, 2])})
    assert json.loads(json.dumps(payload)) == {"integer": 3, "float": 1.5, "nan": None, "array": [1, 2]}
