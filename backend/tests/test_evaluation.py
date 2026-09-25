import copy

import numpy as np
import pandas as pd
import pytest

from backend.detector import detect
from backend.evaluation.metrics import calculate_metrics, group_events
from backend.evaluation.protocol import validate_seed_separation
from backend.evaluation.run import run_synthetic_evaluation
from backend.scoring import persistence_mask, score
from backend.simulator import simulate


def tiny_config():
    return {
        "dataset_version": "test",
        "observations": 60,
        "rolling_window": 5,
        "persistence_length": 3,
        "event_matching_tolerance": 1,
        "model": {"n_estimators": 10, "contamination": 0.06, "random_state": 42},
        "decisions": {
            "isolation_decision_threshold": -0.04,
            "thermal_temperature_threshold": 31.0,
            "payload_temperature_threshold": 33.0,
            "battery_voltage_threshold": 26.5,
            "battery_current_threshold": 3.0,
        },
        "telemanom": {"robust_z_threshold": 6.0},
        "splits": {
            "train": {"normal_seeds": [1, 2]},
            "validation": {"runs": [{"scenario": "normal", "seed": 3}]},
            "test": {"runs": [
                {"scenario": "normal", "seed": 4},
                {"scenario": "thermal_fault", "seed": 5},
                {"scenario": "power_fault", "seed": 6},
            ]},
        },
    }


def test_split_seeds_cannot_overlap():
    config = tiny_config()
    validate_seed_separation(config)
    bad = copy.deepcopy(config)
    bad["splits"]["test"]["runs"][0]["seed"] = 1
    with pytest.raises(ValueError, match="must not overlap"):
        validate_seed_separation(bad)


def test_three_methods_and_persistence_are_separate():
    scored, _, _ = score(detect(simulate("thermal_fault", 180, 42), 42))
    for column in (
        "threshold_candidate", "isolation_candidate", "combined_candidate",
        "confirmed_threshold_event", "confirmed_model_event", "confirmed_combined_event",
        "isolation_decision_score", "anomaly_score",
    ):
        assert column in scored
    assert (scored.combined_candidate == scored.candidate).all()
    assert persistence_mask(pd.Series([True, True, True, False]), 3).tolist() == [False, False, True, False]


def test_event_grouping_and_metric_calculations():
    assert group_events([False, True, True, False, True]) == [
        type(group_events([True])[0])(1, 2),
        type(group_events([True])[0])(4, 4),
    ]
    result = calculate_metrics(
        [np.array([False, True, True, False, False])],
        [np.array([False, False, True, False, True])],
    )
    assert result["point_precision"] == 0.5
    assert result["point_recall"] == 0.5
    assert result["point_f1"] == 0.5
    assert result["false_positive_observations"] == 1
    assert result["false_confirmed_events"] == 1
    assert result["mean_detection_delay_observations"] == 1.0


def test_deterministic_evaluation_metrics():
    first = run_synthetic_evaluation(tiny_config())["test_metrics"]
    second = run_synthetic_evaluation(tiny_config())["test_metrics"]
    for method in ("threshold", "isolation_forest", "combined"):
        ignore = {"processing_time_ms", "model_fit_time_ms"}
        assert {k: v for k, v in first[method].items() if k not in ignore} == {
            k: v for k, v in second[method].items() if k not in ignore
        }


