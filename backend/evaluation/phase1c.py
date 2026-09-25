"""Leakage-safe Telemanom diagnosis, validation calibration, and frozen holdout evaluation."""

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..data.telemanom import available_channels, load_channel
from ..scoring import persistence_mask
from .metrics import calculate_metrics, detection_delays, group_events
from .preprocessing import RobustFeatureScaler, chronological_split
from .run import _telemanom_features


DATA_ROOT = Path("data/external/telemanom")
REPORT_DIR = Path("reports/evaluation")
DEV_CHANNELS = {"SMAP": ["A-1", "A-2", "A-3"], "MSL": ["C-1", "C-2", "D-14"]}
PREVIOUSLY_VIEWED_HOLDOUT = {
    "SMAP": ["G-3", "G-7", "A-9", "E-1", "F-3", "A-8", "E-9", "E-6", "D-4", "E-2"],
    "MSL": ["P-10", "D-15", "T-4", "M-5", "S-2", "M-6", "M-7", "M-2", "T-8", "F-5"],
}
METHODS = ("threshold", "isolation_forest", "combined")
METHOD_PRIORITY = {"threshold": 0, "isolation_forest": 1, "combined": 2}
BASE_CONFIG: dict[str, Any] = {
    "protocol_version": "astra-phase1c-v2",
    "fit_fraction": 0.7,
    "feature_set": "combined",
    "rolling_window": 10,
    "persistence_length": 5,
    "robust_z_multiplier": 6.0,
    "isolation_contamination": 0.02,
    "isolation_estimators": 100,
    "isolation_validation_quantile": 0.01,
    "combined_rule": "or",
    "event_matching_tolerance": 2,
    "random_state": 42,
    "near_constant_epsilon": 1e-8,
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def _hash_config(config: dict[str, Any]) -> str:
    payload = {key: value for key, value in config.items() if key != "configuration_sha256"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_frozen_config(config: dict[str, Any]) -> None:
    if not config.get("frozen"):
        raise ValueError("Configuration is not frozen")
    if config.get("configuration_sha256") != _hash_config(config):
        raise ValueError("Frozen configuration hash mismatch")


def select_holdout_channels(root: Path, count_per_mission: int = 10) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {}
    for mission, excluded in DEV_CHANNELS.items():
        excluded_all = set(excluded) | set(PREVIOUSLY_VIEWED_HOLDOUT[mission])
        candidates = [item for item in available_channels(root, mission) if item not in excluded_all]
        ranked = sorted(candidates, key=lambda item: hashlib.sha256(
            f"astra-phase1c-v2:{mission}:{item}".encode()
        ).hexdigest())
        if len(ranked) < count_per_mission:
            raise ValueError(f"Not enough unevaluated {mission} channels")
        selected[mission] = ranked[:count_per_mission]
    return selected



@dataclass
class ChannelState:
    scaler: RobustFeatureScaler
    model: IsolationForest
    isolation_cutoff: float
    fit_values: np.ndarray
    validation_values: np.ndarray
    model_fit_time_ms: float


def _model_matrix(features: np.ndarray) -> np.ndarray:
    return features if features.shape[1] else np.zeros((len(features), 1), dtype=float)


def fit_channel(values: np.ndarray, config: dict[str, Any]) -> ChannelState:
    fit_values, validation_values = chronological_split(values, config["fit_fraction"])
    scaler = RobustFeatureScaler(
        config["feature_set"], config["rolling_window"], config["near_constant_epsilon"],
    ).fit(fit_values)
    fit_features = _model_matrix(scaler.transform(fit_values))
    history = fit_values[-max(0, config["rolling_window"] - 1):]
    validation_features = _model_matrix(scaler.transform(validation_values, history))
    started = perf_counter()
    model = IsolationForest(
        n_estimators=config["isolation_estimators"],
        contamination=config["isolation_contamination"],
        random_state=config["random_state"],
        n_jobs=1,
    ).fit(fit_features)
    fit_ms = (perf_counter() - started) * 1000
    validation_scores = model.decision_function(validation_features)
    cutoff = float(np.quantile(validation_scores, config["isolation_validation_quantile"]))
    return ChannelState(scaler, model, cutoff, fit_values, validation_values, fit_ms)


def predict_channel(
    state: ChannelState, values: np.ndarray, config: dict[str, Any], history: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, float]]:
    started = perf_counter()
    threshold_candidate = state.scaler.primary_robust_score(values) > config["robust_z_multiplier"]
    threshold = persistence_mask(pd.Series(threshold_candidate), config["persistence_length"]).to_numpy(bool)
    threshold_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    features = _model_matrix(state.scaler.transform(values, history))
    isolation_candidate = state.model.decision_function(features) < state.isolation_cutoff
    isolation = persistence_mask(pd.Series(isolation_candidate), config["persistence_length"]).to_numpy(bool)
    isolation_ms = (perf_counter() - started) * 1000

    started = perf_counter()
    if config["combined_rule"] == "or":
        combined_candidate = threshold_candidate | isolation_candidate
    elif config["combined_rule"] == "and":
        combined_candidate = threshold_candidate & isolation_candidate
    else:
        raise ValueError("combined_rule must be 'or' or 'and'")
    combined = persistence_mask(pd.Series(combined_candidate), config["persistence_length"]).to_numpy(bool)
    combined_ms = (perf_counter() - started) * 1000
    return (
        {"threshold": threshold, "isolation_forest": isolation, "combined": combined},
        {
            "threshold": threshold_ms,
            "isolation_forest": state.model_fit_time_ms + isolation_ms,
            "combined": state.model_fit_time_ms + threshold_ms + isolation_ms + combined_ms,
        },
    )


def _inject_validation_fault(values: np.ndarray, scaler: RobustFeatureScaler, channel: str) -> tuple[np.ndarray, np.ndarray]:
    injected = values.copy()
    onset = max(1, int(len(injected) * 0.6))
    truth = np.zeros(len(injected), dtype=bool)
    truth[onset:] = True
    scale = max(float(scaler.scale_[0]), 1e-6)
    direction = 1.0 if int(hashlib.sha256(channel.encode()).hexdigest(), 16) % 2 else -1.0
    injected[onset:, 0] += direction * np.linspace(2.0 * scale, 8.0 * scale, len(injected) - onset)
    return injected, truth


def macro_average(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, float | None]:
    result: dict[str, float | None] = {}
    for key in keys:
        values = [row[key] for row in rows if row.get(key) is not None]
        result[key] = round(float(np.mean(values)), 6) if values else None
    return result

def _best_method(metrics: dict[str, dict[str, Any]]) -> str:
    return max(METHODS, key=lambda method: (
        metrics[method]["point_f1"],
        metrics[method]["event_recall"] or 0.0,
        -metrics[method]["false_alerts_per_1000_observations"],
        -METHOD_PRIORITY[method],
    ))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(_json_safe(rows))


def diagnose_development(root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    """Record Phase 1B behavior before any Phase 1C parameter selection."""
    rows: list[dict[str, Any]] = []
    for mission, channels in DEV_CHANNELS.items():
        for channel in channels:
            train, test = load_channel(root, channel)
            train_values = train.frame[train.value_columns].to_numpy(float)
            test_values = test.frame[test.value_columns].to_numpy(float)
            truth = test.frame.ground_truth_anomaly.to_numpy(bool)
            primary_train, primary_test = train_values[:, 0], test_values[:, 0]
            finite_train = primary_train[np.isfinite(primary_train)]
            median = float(np.median(finite_train))
            scale = max(1e-9, 1.4826 * float(np.median(np.abs(finite_train - median))))
            threshold_started = perf_counter()
            threshold_candidate = np.abs((np.nan_to_num(primary_test, nan=median) - median) / scale) > 6.0
            threshold = persistence_mask(pd.Series(threshold_candidate), 3).to_numpy(bool)
            threshold_processing = (perf_counter() - threshold_started) * 1000
            train_features = _telemanom_features(np.nan_to_num(train_values), 5)
            test_features = _telemanom_features(np.nan_to_num(test_values), 5)
            started = perf_counter()
            model = IsolationForest(n_estimators=100, contamination=0.06, random_state=42, n_jobs=1).fit(train_features)
            train_scores = model.decision_function(train_features)
            test_scores = model.decision_function(test_features)
            isolation = persistence_mask(pd.Series(test_scores < -0.04), 3).to_numpy(bool)
            processing = (perf_counter() - started) * 1000
            combined = persistence_mask(pd.Series(threshold_candidate | (test_scores < -0.04)), 3).to_numpy(bool)
            method_metrics = {
                "threshold": calculate_metrics([truth], [threshold], 2),
                "isolation_forest": calculate_metrics([truth], [isolation], 2),
                "combined": calculate_metrics([truth], [combined], 2),
            }
            feature_std = np.nanstd(train_values, axis=0)
            base = {
                "mission": mission,
                "channel": channel,
                "training_observations": len(train_values),
                "test_observations": len(test_values),
                "labelled_intervals": len(group_events(truth)),
                "anomalous_point_percentage": round(float(np.mean(truth) * 100), 6),
                "missing_value_percentage": round(float(np.mean(~np.isfinite(np.vstack([train_values, test_values]))) * 100), 6),
                "train_mean": round(float(np.nanmean(primary_train)), 6),
                "train_std": round(float(np.nanstd(primary_train)), 6),
                "train_min": round(float(np.nanmin(primary_train)), 6),
                "train_max": round(float(np.nanmax(primary_train)), 6),
                "test_mean": round(float(np.nanmean(primary_test)), 6),
                "test_std": round(float(np.nanstd(primary_test)), 6),
                "test_min": round(float(np.nanmin(primary_test)), 6),
                "test_max": round(float(np.nanmax(primary_test)), 6),
                "standardized_mean_shift": round(float(abs(np.nanmean(primary_test) - np.nanmean(primary_train)) / max(np.nanstd(primary_train), 1e-9)), 6),
                "test_to_train_std_ratio": round(float(np.nanstd(primary_test) / max(np.nanstd(primary_train), 1e-9)), 6),
                "test_outside_train_range_percentage": round(float(np.mean((primary_test < np.nanmin(primary_train)) | (primary_test > np.nanmax(primary_train))) * 100), 6),
                "test_difference_std": round(float(np.nanstd(np.diff(primary_test))), 6),
                "test_linear_slope": round(float(np.polyfit(np.arange(len(primary_test)), np.nan_to_num(primary_test, nan=np.nanmean(primary_test)), 1)[0]), 9),
                "constant_or_near_constant_features": int(np.sum(feature_std <= 1e-8)),
                "threshold_candidate_percentage": round(float(np.mean(threshold_candidate) * 100), 6),
                "if_score_direction_valid": bool(np.nanmean(test_scores[truth]) < np.nanmean(test_scores[~truth])) if truth.any() and (~truth).any() else None,
                "if_train_score_mean": round(float(np.mean(train_scores)), 6),
                "if_test_normal_score_mean": round(float(np.mean(test_scores[~truth])), 6),
                "rolling_boundary_candidate_in_first_window": bool(np.any(threshold_candidate[:5] | (test_scores[:5] < -0.04))),
                "best_performing_method": _best_method(method_metrics),
            }
            for method, metrics in method_metrics.items():
                for key, value in metrics.items():
                    base[f"{method}_{key}"] = value
                base[f"{method}_processing_time_ms"] = round(threshold_processing if method == "threshold" else processing, 3)
            rows.append(base)
    _write_csv(REPORT_DIR / "phase1c_development_channels.csv", rows)
    lines = [
        "# Phase 1C development-channel diagnosis", "",
        "These six official test channels were already viewed in Phase 1B. They are diagnostic data, not holdout evidence. No Phase 1C parameter was selected from their labels or test metrics.", "",
        "| Mission | Channel | Train / test | Events | Anomaly % | Mean shift (train SD) | Outside train range % | Constant features | Threshold F1 | IF F1 | Combined F1 | Best |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['mission']} | {row['channel']} | {row['training_observations']} / {row['test_observations']} | {row['labelled_intervals']} | {row['anomalous_point_percentage']:.3f} | {row['standardized_mean_shift']:.3f} | {row['test_outside_train_range_percentage']:.3f} | {row['constant_or_near_constant_features']} | {row['threshold_point_f1']:.4f} | {row['isolation_forest_point_f1']:.4f} | {row['combined_point_f1']:.4f} | {row['best_performing_method']} |"
        )
    lines += [
        "", "## Findings recorded before calibration", "",
        "- Several channels have strong train-to-test level or range shift. A fixed train-median robust threshold therefore creates long alerts before labelled events.",
        "- The legacy Isolation Forest cutoff is too conservative on some channels and its unscaled mixed features are dominated by channel-specific ranges and command indicators.",
        "- Every channel contains near-constant command features. They add dimensions without useful variance and can distort distance-based splits.",
        "- The legacy test feature calculation starts rolling windows with no training history, creating avoidable boundary differences.",
        "- Persistence suppresses isolated points but cannot repair a threshold that remains active through a shifted normal regime.",
        "- Isolation Forest score direction is reported per channel; `decision_function` is lower for more unusual samples. Direction checks that fail show score ordering does not align with labels, not a reversed comparator.",
        "- Event matching rejects alerts that began more than two observations before a labelled interval, so long pre-existing alerts cannot claim later events. Tolerated early starts are recorded as zero delay.",
        "- The public archive is already pre-scaled by its publisher. Phase 1C still applies train-only per-channel robust scaling; the source archive's upstream scaling cannot be undone.",
    ]
    (REPORT_DIR / "phase1c_development_channels.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def calibration_grid(feature_set: str | None = None) -> list[dict[str, Any]]:
    if feature_set is None:
        variants = [{"feature_set": name} for name in ("raw", "rolling", "difference", "combined")]
    else:
        variants = [
            {"feature_set": feature_set},
            {"feature_set": feature_set, "robust_z_multiplier": 4.0},
            {"feature_set": feature_set, "robust_z_multiplier": 8.0},
            {"feature_set": feature_set, "rolling_window": 5},
            {"feature_set": feature_set, "rolling_window": 15},
            {"feature_set": feature_set, "persistence_length": 3},
            {"feature_set": feature_set, "persistence_length": 7},
            {"feature_set": feature_set, "isolation_contamination": 0.01},
            {"feature_set": feature_set, "isolation_contamination": 0.04},
            {"feature_set": feature_set, "isolation_estimators": 50},
            {"feature_set": feature_set, "isolation_estimators": 150},
            {"feature_set": feature_set, "combined_rule": "and"},
        ]
    unique: dict[str, dict[str, Any]] = {}
    for changes in variants:
        config = {**BASE_CONFIG, **changes}
        key = json.dumps(config, sort_keys=True)
        unique[key] = config
    return list(unique.values())

def _calibration_result(config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    normal_truths: list[np.ndarray] = []
    synthetic_truths: list[np.ndarray] = []
    normal_predictions = {method: [] for method in METHODS}
    synthetic_predictions = {method: [] for method in METHODS}
    per_channel_synthetic_f1 = {method: [] for method in METHODS}
    for mission, channels in DEV_CHANNELS.items():
        for channel in channels:
            train, _ = load_channel(root, channel)
            values = train.frame[train.value_columns].to_numpy(float)
            state = fit_channel(values, config)
            history = state.fit_values[-max(0, config["rolling_window"] - 1):]
            normal_masks, _ = predict_channel(state, state.validation_values, config, history)
            injected, truth = _inject_validation_fault(state.validation_values, state.scaler, f"{mission}:{channel}")
            synthetic_masks, _ = predict_channel(state, injected, config, history)
            normal_truth = np.zeros(len(state.validation_values), dtype=bool)
            normal_truths.append(normal_truth)
            synthetic_truths.append(truth)
            for method in METHODS:
                normal_predictions[method].append(normal_masks[method])
                synthetic_predictions[method].append(synthetic_masks[method])
                per_channel_synthetic_f1[method].append(calculate_metrics([truth], [synthetic_masks[method]], 2)["point_f1"])
    rows = []
    for method in METHODS:
        normal = calculate_metrics(normal_truths, normal_predictions[method], config["event_matching_tolerance"])
        synthetic = calculate_metrics(synthetic_truths, synthetic_predictions[method], config["event_matching_tolerance"])
        score = synthetic["point_f1"] - 2.0 * normal["point_false_positive_rate"] - 0.002 * normal["false_alerts_per_1000_observations"] - 0.1 * float(np.std(per_channel_synthetic_f1[method]))
        rows.append({
            "method": method,
            **config,
            "normal_validation_point_fpr": normal["point_false_positive_rate"],
            "normal_validation_false_alerts_per_1000": normal["false_alerts_per_1000_observations"],
            "synthetic_validation_point_precision": synthetic["point_precision"],
            "synthetic_validation_point_recall": synthetic["point_recall"],
            "synthetic_validation_point_f1": synthetic["point_f1"],
            "synthetic_validation_event_recall": synthetic["event_recall"],
            "synthetic_validation_f1_std_across_channels": round(float(np.std(per_channel_synthetic_f1[method])), 6),
            "selection_score": round(float(score), 9),
        })
    return rows


def calibrate(root: Path = DATA_ROOT) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, config in enumerate(calibration_grid(), start=1):
        config_rows = _calibration_result(config, root)
        for row in config_rows:
            row["configuration_id"] = f"A{index:02d}"
        rows.extend(config_rows)
    ablation_combined = [row for row in rows if row["method"] == "combined"]
    controlled_ablation = [row for row in ablation_combined if row["normal_validation_point_fpr"] <= 0.01]
    feature_pool = controlled_ablation or ablation_combined
    selected_feature = max(feature_pool, key=lambda row: (
        row["selection_score"], -row["normal_validation_point_fpr"],
    ))["feature_set"]
    for index, config in enumerate(calibration_grid(selected_feature), start=1):
        config_rows = _calibration_result(config, root)
        for row in config_rows:
            row["configuration_id"] = f"P{index:02d}"
        rows.extend(config_rows)
    _write_csv(REPORT_DIR / "phase1c_calibration.csv", rows)
    parameter_rows = [row for row in rows if row["method"] == "combined" and row["configuration_id"].startswith("P")]
    controlled = [row for row in parameter_rows if row["normal_validation_point_fpr"] <= 0.01]
    pool = controlled or parameter_rows
    selected_row = max(pool, key=lambda row: (row["selection_score"], -row["normal_validation_point_fpr"], -row["isolation_estimators"]))
    selected = {key: selected_row[key] for key in BASE_CONFIG}
    selected.update({
        "frozen": True,
        "selection_basis": "Feature ablation followed by a one-factor parameter search. Selection uses normal public train-validation false alerts and separately labelled synthetic validation sensitivity; no official test labels or results used",
        "selected_configuration_id": selected_row["configuration_id"],
        "selected_feature_ablation": selected_feature,
        "normal_validation_point_fpr": selected_row["normal_validation_point_fpr"],
        "synthetic_validation_point_f1": selected_row["synthetic_validation_point_f1"],
        "synthetic_validation_event_recall": selected_row["synthetic_validation_event_recall"],
        "features_retained_by_definition": list({
            "raw": ["raw", "missing"],
            "rolling": ["raw", "rolling_mean", "rolling_std", "rolling_slope", "missing"],
            "difference": ["raw", "difference", "missing"],
            "combined": ["raw", "difference", "rolling_mean", "rolling_std", "rolling_slope", "missing"],
        }[selected["feature_set"]]),
        "event_matching_rule": "Detected event start must be inside a labelled interval or within tolerance; pre-existing alerts outside tolerance do not match; tolerated early starts have zero delay",
    })
    selected["configuration_sha256"] = _hash_config(selected)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "phase1c_selected_config.json").write_text(json.dumps(_json_safe(selected), indent=2) + "\n", encoding="utf-8")
    # This diagnostic comparison runs only after selection and cannot alter the frozen config.
    development_rows, development_aggregates = evaluate_channels(DEV_CHANNELS, selected, root)
    _write_csv(REPORT_DIR / "phase1c_development_after_calibration.csv", development_rows)
    (REPORT_DIR / "phase1c_development_after_calibration.json").write_text(
        json.dumps(_json_safe({"per_channel": development_rows, **development_aggregates}), indent=2) + "\n",
        encoding="utf-8",
    )
    return selected

def evaluate_channels(
    channel_map: dict[str, list[str]], config: dict[str, Any], root: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    per_channel: list[dict[str, Any]] = []
    all_truths: list[np.ndarray] = []
    all_predictions = {method: [] for method in METHODS}
    method_times = {method: 0.0 for method in METHODS}
    for mission, channels in channel_map.items():
        for channel in channels:
            train, test = load_channel(root, channel)
            train_values = train.frame[train.value_columns].to_numpy(float)
            test_values = test.frame[test.value_columns].to_numpy(float)
            truth = test.frame.ground_truth_anomaly.to_numpy(bool)
            state = fit_channel(train_values, config)
            history = train_values[-max(0, config["rolling_window"] - 1):]
            masks, times = predict_channel(state, test_values, config, history)
            metrics_by_method = {}
            for method in METHODS:
                metrics = calculate_metrics([truth], [masks[method]], config["event_matching_tolerance"])
                metrics["processing_time_ms"] = round(times[method], 3)
                metrics_by_method[method] = metrics
                method_times[method] += times[method]
                all_predictions[method].append(masks[method])
            all_truths.append(truth)
            best = _best_method(metrics_by_method)
            for method in METHODS:
                per_channel.append({"mission": mission, "channel": channel, "method": method, "best_method": best, **metrics_by_method[method]})

    micro: dict[str, Any] = {}
    macro: dict[str, Any] = {}
    delays: dict[str, Any] = {}
    wins = {method: 0 for method in METHODS}
    for mission, channels in channel_map.items():
        for channel in channels:
            row = next(item for item in per_channel if item["mission"] == mission and item["channel"] == channel)
            wins[row["best_method"]] += 1
    macro_keys = ("point_precision", "point_recall", "point_f1", "point_false_positive_rate", "event_recall", "false_alerts_per_1000_observations", "mean_detection_delay_observations")
    for method in METHODS:
        micro[method] = calculate_metrics(all_truths, all_predictions[method], config["event_matching_tolerance"])
        micro[method]["processing_time_ms"] = round(method_times[method], 3)
        method_rows = [row for row in per_channel if row["method"] == method]
        macro[method] = macro_average(method_rows, macro_keys)

        matched = detection_delays(all_truths, all_predictions[method], config["event_matching_tolerance"])
        delays[method] = {
            "count": len(matched),
            "minimum": min(matched) if matched else None,
            "median": round(float(np.median(matched)), 6) if matched else None,
            "p90": round(float(np.percentile(matched, 90)), 6) if matched else None,
            "maximum": max(matched) if matched else None,
        }
    return per_channel, {"micro": micro, "macro": macro, "detection_delay_distribution": delays, "channel_wins": wins}


def _method_judgement(aggregates: dict[str, Any]) -> tuple[str, str]:
    micro = aggregates["micro"]
    baseline, combined = micro["threshold"], micro["combined"]
    clearly_better = (
        combined["point_f1"] > baseline["point_f1"]
        and (combined["event_recall"] or 0) >= (baseline["event_recall"] or 0)
        and combined["false_alerts_per_1000_observations"] <= baseline["false_alerts_per_1000_observations"]
    )
    if clearly_better:
        return "combined", "Combined improved point F1 without reducing event recall or increasing false-alert rate on the frozen holdout."
    best = max(("threshold", "isolation_forest"), key=lambda method: (
        micro[method]["point_f1"], micro[method]["event_recall"] or 0,
        -micro[method]["false_alerts_per_1000_observations"], -METHOD_PRIORITY[method],
    ))
    return best, "Combined did not clear the predeclared bar of higher point F1, no lower event recall, and no higher false-alert rate; the stronger simpler baseline is preferred."


def run_holdout(root: Path = DATA_ROOT) -> dict[str, Any]:
    config_path = REPORT_DIR / "phase1c_selected_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    verify_frozen_config(config)
    channels = select_holdout_channels(root)
    manifest = {
        "selection_rule": "For each mission, exclude development and invalidated initial-run channels, rank remaining channel IDs by SHA-256 of 'astra-phase1c-v2:<mission>:<channel>', and take the first 10",
        "selected_channels": channels,
        "excluded_development_channels": DEV_CHANNELS,
        "excluded_previously_viewed_channels": PREVIOUSLY_VIEWED_HOLDOUT,
        "configuration_sha256": config["configuration_sha256"],
        "performance_not_calculated_when_manifest_written": True,
    }
    manifest_path = REPORT_DIR / "phase1c_holdout_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    per_channel, aggregates = evaluate_channels(channels, config, root)
    recommendation, rationale = _method_judgement(aggregates)
    result = {
        "data_source": "Official Telemanom SMAP/MSL archive",
        "public_data_status": "Frozen unseen-channel holdout; official test labels used only for final evaluation",
        "manifest": manifest,
        "frozen_configuration": config,
        "per_channel": per_channel,
        **aggregates,
        "recommended_public_detector": recommendation,
        "combined_detector_judgement": rationale,
        "operational_readiness": False,
    }
    (REPORT_DIR / "phase1c_holdout_results.json").write_text(json.dumps(_json_safe(result), indent=2) + "\n", encoding="utf-8")
    _write_csv(REPORT_DIR / "phase1c_holdout_results.csv", per_channel)
    _write_results_markdown(result)
    return result


def _write_results_markdown(result: dict[str, Any]) -> None:
    config = result["frozen_configuration"]
    lines = [
        "# ASTRA Phase 1C results", "",
        "This is offline research evidence on anonymized, pre-scaled public telemetry. It does not establish operational readiness.", "",
        "## Frozen protocol", "",
        f"- Configuration hash: `{config['configuration_sha256']}`",
        f"- Features: `{config['feature_set']}`; window {config['rolling_window']}; persistence {config['persistence_length']}",
        f"- Robust threshold: {config['robust_z_multiplier']} train-fitted robust scale units",
        f"- Isolation Forest: contamination {config['isolation_contamination']}, estimators {config['isolation_estimators']}, validation score quantile {config['isolation_validation_quantile']}",
        f"- Combined rule: `{config['combined_rule']}`",
        "- Preprocessing and Isolation Forest fit only the first chronological part of each official training array. The later training portion calibrates normal false alerts and the model score cutoff. Official test arrays remain untouched until final evaluation.",
        "- Synthetic validation ramps are labelled synthetic and are used only to compare sensitivity. They are not NASA anomalies.", "",
        "## Holdout channels", "",
    ]
    for mission, channels in result["manifest"]["selected_channels"].items():
        lines.append(f"- {mission}: {', '.join(channels)}")
    calibration = pd.read_csv(REPORT_DIR / "phase1c_calibration.csv")
    ablations = calibration[(calibration.method == "combined") & calibration.configuration_id.str.startswith("A")]
    development_after = json.loads((REPORT_DIR / "phase1c_development_after_calibration.json").read_text(encoding="utf-8"))["micro"]["combined"]
    lines += [
        "", "## Protocol audit", "",
        "An initial holdout execution was invalidated because parameter variants had not been tested with the feature set favored by the ablation. Its artifacts are preserved with the `phase1c_invalidated_initial_` prefix and none of its channels appear in the final holdout. The correction was driven by validation-protocol structure, not by holdout performance.", "",
        "## Validation-only feature ablation", "",
        "| Feature set | Normal validation FPR | Synthetic validation F1 | Synthetic event recall | Selection score |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in ablations.iterrows():
        lines.append(f"| {row['feature_set']} | {row['normal_validation_point_fpr']:.6f} | {row['synthetic_validation_point_f1']:.6f} | {row['synthetic_validation_event_recall']:.6f} | {row['selection_score']:.6f} |")
    lines += [
        "", "Rolling features won the controlled ablation. First difference was removed. The missing-value indicator is retained so missingness first appearing after fitting remains observable; train-constant telemetry-derived features are removed per channel.", "",
        "## Development channels before and after calibration", "",
        "Phase 1B combined results were SMAP F1 0.018843 / point FPR 0.350946 / event recall 0.000000, and MSL F1 0.256133 / point FPR 0.227468 / event recall 0.833333. Those mission aggregates are retained in the Phase 1B report.", "",
        f"Across all six channels after the frozen Phase 1C calibration, combined F1 was {development_after['point_f1']:.6f}, point FPR {development_after['point_false_positive_rate']:.6f}, event recall {(development_after['event_recall'] or 0):.6f}, and false alerts/1,000 {development_after['false_alerts_per_1000_observations']:.6f}.", "",
        "The false-positive rate improved sharply, but event recall fell. This is calibration trade-off evidence, not a claim that every metric improved.", "",
        "## Micro results", "", "| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay | Time ms |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        row = result["micro"][method]
        lines.append(f"| {method} | {row['point_precision']:.6f} | {row['point_recall']:.6f} | {row['point_f1']:.6f} | {row['point_false_positive_rate']:.6f} | {(row['event_recall'] or 0):.6f} | {row['false_alerts_per_1000_observations']:.6f} | {row['mean_detection_delay_observations'] if row['mean_detection_delay_observations'] is not None else '—'} | {row['processing_time_ms']:.3f} |")
    lines += ["", "## Macro results", "", "| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for method in METHODS:
        row = result["macro"][method]
        lines.append(f"| {method} | {row['point_precision']:.6f} | {row['point_recall']:.6f} | {row['point_f1']:.6f} | {row['point_false_positive_rate']:.6f} | {(row['event_recall'] or 0):.6f} | {row['false_alerts_per_1000_observations']:.6f} | {row['mean_detection_delay_observations'] if row['mean_detection_delay_observations'] is not None else '—'} |")
    lines += ["", "## Mission macro comparison", "", "| Mission | Method | F1 | Event recall | Point FPR | False alerts / 1,000 |", "|---|---|---:|---:|---:|---:|"]
    for mission in ("SMAP", "MSL"):
        for method in METHODS:
            mission_rows = [row for row in result["per_channel"] if row["mission"] == mission and row["method"] == method]
            summary = macro_average(mission_rows, ("point_f1", "event_recall", "point_false_positive_rate", "false_alerts_per_1000_observations"))
            lines.append(f"| {mission} | {method} | {summary['point_f1']:.6f} | {(summary['event_recall'] or 0):.6f} | {summary['point_false_positive_rate']:.6f} | {summary['false_alerts_per_1000_observations']:.6f} |")
    lines += ["", "## Detection-delay distribution", "", "| Method | Matches | Minimum | Median | P90 | Maximum |", "|---|---:|---:|---:|---:|---:|"]
    for method in METHODS:
        delay = result["detection_delay_distribution"][method]
        lines.append(f"| {method} | {delay['count']} | {delay['minimum'] if delay['minimum'] is not None else '-'} | {delay['median'] if delay['median'] is not None else '-'} | {delay['p90'] if delay['p90'] is not None else '-'} | {delay['maximum'] if delay['maximum'] is not None else '-'} |")
    lines += ["", "## Per-channel results", "", "| Mission | Channel | Method | F1 | Event recall | Point FPR | False alerts / 1,000 | Mean delay | Best |", "|---|---|---|---:|---:|---:|---:|---:|---|"]
    for row in result["per_channel"]:
        lines.append(f"| {row['mission']} | {row['channel']} | {row['method']} | {row['point_f1']:.6f} | {(row['event_recall'] or 0):.6f} | {row['point_false_positive_rate']:.6f} | {row['false_alerts_per_1000_observations']:.6f} | {row['mean_detection_delay_observations'] if row['mean_detection_delay_observations'] is not None else '—'} | {row['best_method']} |")
    lines += [
        "", "## Decision", "",
        f"Recommended public-data method: **{result['recommended_public_detector']}**.", "",
        result["combined_detector_judgement"], "",
        f"Channel wins: {result['channel_wins']}.", "",
        "An LSTM experiment is not justified by this phase alone. A sequence model would add complexity before the simpler baselines show stable cross-channel calibration, and the current anonymized channel-by-channel protocol lacks a defensible sequence-training target.", "",
        "## Limitations", "",
        "- Telemanom channels are anonymized and pre-scaled upstream; physical units and exact mission timing are unavailable.",
        "- Public training arrays are treated as normal because they contain no official interval labels; undetected contamination may exist.",
        "- Synthetic validation ramps test sensitivity to one artificial pattern and cannot represent all spacecraft anomalies.",
        "- One frozen 20-channel holdout is evidence for this protocol only. It is not an operational qualification.",
        "- Timing is machine-dependent and includes per-channel model fitting for Isolation Forest and combined methods.",
    ]
    (REPORT_DIR / "PHASE1C_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="ASTRA Phase 1C evaluation")
    parser.add_argument("command", choices=("diagnose", "calibrate", "holdout", "all"))
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    args = parser.parse_args()
    if args.command in ("diagnose", "all"):
        diagnose_development(args.data_root)
        print("Development diagnostics written before calibration.")
    if args.command in ("calibrate", "all"):
        selected = calibrate(args.data_root)
        print(json.dumps(selected, indent=2))
    if args.command in ("holdout", "all"):
        result = run_holdout(args.data_root)
        print(json.dumps(result["micro"], indent=2))


if __name__ == "__main__":
    main()
