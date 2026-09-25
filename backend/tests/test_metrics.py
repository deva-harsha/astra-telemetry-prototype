import numpy as np
import pytest

from backend.evaluation.metrics import Interval, calculate_metrics, group_events
from backend.evaluation.protocol import validate_seed_separation


def test_event_grouping():
    assert group_events([False, True, True, False, True]) == [Interval(1, 2), Interval(4, 4)]


def test_precision_recall_f1_false_alerts_and_detection_delay():
    result = calculate_metrics(
        [np.array([False, True, True, False, False])],
        [np.array([False, False, True, False, True])],
    )
    assert result["point_precision"] == 0.5
    assert result["point_recall"] == 0.5
    assert result["point_f1"] == 0.5
    assert result["false_positive_observations"] == 1
    assert result["point_false_positive_rate"] == 0.333333
    assert result["false_confirmed_events"] == 1
    assert result["false_alerts_per_1000_observations"] == 200.0
    assert result["mean_detection_delay_observations"] == 1.0


def test_seed_overlap_is_rejected():
    config = {
        "splits": {
            "train": {"normal_seeds": [1, 2]},
            "validation": {"runs": [{"seed": 3}]},
            "test": {"runs": [{"seed": 1}]},
        }
    }
    with pytest.raises(ValueError, match="must not overlap"):
        validate_seed_separation(config)



def test_preexisting_alert_does_not_claim_later_event():
    result = calculate_metrics(
        [np.array([False] * 10 + [True] * 5)],
        [np.array([True] * 15)],
        tolerance=2,
    )
    assert result["event_recall"] == 0.0
    assert result["false_confirmed_events"] == 1
    assert result["mean_detection_delay_observations"] is None

