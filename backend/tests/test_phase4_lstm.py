import json

import numpy as np
import pytest

from backend.evaluation.lstm_autoencoder import (
    TrainOnlyRobustScaler,
    align_window_scores,
    configuration_hash,
    freeze_configuration,
    json_safe,
    make_sequences,
    mean_per_feature_error,
    persistence_decision,
    select_unseen_holdout,
    set_deterministic_seeds,
    validation_threshold,
    verify_frozen_configuration,
)


def test_sequence_windows_are_chronological_and_aligned():
    values = np.arange(12, dtype=float).reshape(6, 2)
    batch = make_sequences(values, 3)
    assert batch.end_indices.tolist() == [2, 3, 4, 5]
    assert np.array_equal(batch.windows[0], values[:3])
    assert np.array_equal(batch.windows[-1], values[-3:])


def test_windows_never_cross_boundaries():
    values = np.arange(8, dtype=float).reshape(8, 1)
    boundaries = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    batch = make_sequences(values, 3, boundary_ids=boundaries)
    assert batch.end_indices.tolist() == [2, 3, 6, 7]
    assert batch.boundary_ids.tolist() == [0, 0, 1, 1]


def test_scaler_fits_training_only_and_removes_constant_features():
    train = np.array([[1.0, 5.0], [2.0, 5.0], [3.0, 5.0]])
    validation = np.array([[1000.0, 1000.0]])
    scaler = TrainOnlyRobustScaler().fit(train, ["telemetry", "constant"])
    before = scaler.center_.copy()
    transformed = scaler.transform(validation)
    assert np.array_equal(before, scaler.center_)
    assert scaler.retained_features == ["telemetry"]
    assert scaler.removed_features == ["constant"]
    assert transformed.shape == (1, 1)


def test_score_alignment_leaves_sequence_warmup_explicit():
    aligned = align_window_scores(np.array([0.1, 0.2]), np.array([2, 3]), 4)
    assert np.isnan(aligned[:2]).all()
    assert aligned[2:].tolist() == [0.1, 0.2]


def test_validation_threshold_uses_only_given_errors():
    assert validation_threshold(np.array([1.0, 2.0, 3.0, 4.0]), 0.75) == pytest.approx(3.25)
    with pytest.raises(ValueError):
        validation_threshold(np.array([1.0]), 1.0)


def test_deterministic_seed_controls_numpy():
    set_deterministic_seeds(42)
    first = np.random.random(4)
    set_deterministic_seeds(42)
    assert np.array_equal(first, np.random.random(4))


def test_configuration_freeze_detects_mutation():
    frozen = freeze_configuration({"window_size": 20, "gate": {"macro_f1_gain": 0.02}})
    verify_frozen_configuration(frozen)
    assert frozen["configuration_sha256"] == configuration_hash(frozen)
    frozen["window_size"] = 40
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_frozen_configuration(frozen)


def test_holdout_selection_excludes_every_prior_channel():
    selected, limitations = select_unseen_holdout(
        {"SMAP": ["A", "B", "C"], "MSL": ["D", "E"]},
        {"SMAP": ["A"], "MSL": ["D"]},
        requested_per_mission=2,
        salt="test",
    )
    assert "A" not in selected["SMAP"] and "D" not in selected["MSL"]
    assert len(selected["SMAP"]) == 2
    assert len(selected["MSL"]) == 1
    assert limitations


def test_metrics_are_json_safe_and_detection_delay_non_negative():
    document = json_safe({"score": np.float64(0.3), "missing": np.nan, "count": np.int64(2)})
    assert json.loads(json.dumps(document)) == {"score": 0.3, "missing": None, "count": 2}
    decision = persistence_decision(np.array([False, True, True, True]), 3)
    assert decision.tolist() == [False, False, False, True]
    assert np.flatnonzero(decision)[0] - 1 >= 0


def test_per_feature_reconstruction_error():
    values = np.zeros((2, 3, 2))
    rebuilt = values.copy()
    rebuilt[:, :, 0] = 1.0
    rebuilt[:, :, 1] = 2.0
    assert mean_per_feature_error(values, rebuilt).tolist() == [1.0, 2.0]

def test_optional_pytorch_training_is_deterministic():
    pytest.importorskip("torch")
    from backend.evaluation.lstm_autoencoder import reconstruction_errors, train_autoencoder
    rng = np.random.default_rng(7)
    train = rng.normal(size=(12, 5, 1)).astype(np.float32)
    validation = rng.normal(size=(6, 5, 1)).astype(np.float32)
    config = {"random_seed": 42, "latent_units": 2, "lstm_layers": 1, "loss": "mae", "learning_rate": 0.001, "batch_size": 4, "early_stopping_patience": 2, "early_stopping_min_delta": 1e-6, "max_epochs": 2}
    first, history_one = train_autoencoder(train, validation, config)
    second, history_two = train_autoencoder(train, validation, config)
    first_errors, _ = reconstruction_errors(first, validation)
    second_errors, _ = reconstruction_errors(second, validation)
    assert history_one == history_two
    assert np.array_equal(first_errors, second_errors)

def test_phase4_frozen_artifacts_exclude_all_prior_channels():
    from pathlib import Path
    frozen = json.loads(Path('reports/evaluation/phase4_lstm_frozen_config.json').read_text())
    manifest = json.loads(Path('reports/evaluation/phase4_lstm_holdout_manifest.json').read_text())
    phase1c = json.loads(Path('reports/evaluation/phase1c_holdout_manifest.json').read_text())
    invalidated = json.loads(Path('reports/evaluation/phase1c_invalidated_initial_holdout_manifest.json').read_text())
    verify_frozen_configuration(frozen)
    assert manifest['performance_not_calculated_when_manifest_written'] is True
    assert manifest['frozen_configuration_sha256'] == frozen['configuration_sha256']
    for mission, selected in manifest['selected_channels'].items():
        forbidden = set(frozen['development_channels'][mission]) | set(phase1c['selected_channels'][mission]) | set(invalidated['selected_channels'][mission])
        assert forbidden.isdisjoint(selected)

def test_phase4_final_evidence_is_json_safe_aligned_and_non_negative():
    from pathlib import Path
    result = json.loads(Path('reports/evaluation/phase4_lstm_holdout_results.json').read_text())
    json.dumps(result, allow_nan=False)
    window = result['frozen_configuration']['window_size']
    for distribution in result['detection_delay_distribution'].values():
        for key in ('mean', 'median', 'p90', 'maximum'):
            assert distribution[key] is None or distribution[key] >= 0
    for evidence in result['reconstruction_evidence']:
        assert all(value >= 0 for value in evidence['per_feature_reconstruction_error'].values())
        if evidence['window_end_index'] is not None:
            assert evidence['window_end_index'] - evidence['window_start_index'] + 1 == window
