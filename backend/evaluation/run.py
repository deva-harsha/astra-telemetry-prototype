import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..data.telemanom import available_channels, load_channel
from ..detector import detect, fit_isolation_forest, rolling_features
from ..scoring import persistence_mask, score
from ..simulator import simulate
from .metrics import calculate_metrics
from .protocol import load_config


DEFAULT_CONFIG = Path("backend/evaluation/configs/default.json")
DEFAULT_TELEMANOM_ROOT = Path("data/external/telemanom")
REPORT_DIRECTORY = Path("reports/evaluation")
METHODS = ("threshold", "isolation_forest", "combined")


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _prediction_columns(scored: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "threshold": scored.confirmed_threshold_event.to_numpy(dtype=bool),
        "isolation_forest": scored.confirmed_model_event.to_numpy(dtype=bool),
        "combined": scored.confirmed_combined_event.to_numpy(dtype=bool),
    }


def _evaluate_synthetic_runs(
    runs: list[dict[str, Any]], config: dict[str, Any], model: IsolationForest,
) -> tuple[dict[str, dict[str, Any]], dict[str, float]]:
    truths: list[np.ndarray] = []
    predictions = {method: [] for method in METHODS}
    timings = {method: 0.0 for method in METHODS}
    decisions = config["decisions"]
    persistence = config["persistence_length"]

    for run in runs:
        frame = simulate(run["scenario"], config["observations"], int(run["seed"]))
        truths.append(frame.fault_active.to_numpy(dtype=bool))

        started = perf_counter()
        threshold_candidate = (
            (frame.battery_temperature > decisions["thermal_temperature_threshold"])
            | (frame.payload_temperature > decisions["payload_temperature_threshold"])
            | (frame.battery_voltage < decisions["battery_voltage_threshold"])
            | (frame.battery_current > decisions["battery_current_threshold"])
        )
        threshold_prediction = persistence_mask(threshold_candidate, persistence).to_numpy()
        timings["threshold"] += (perf_counter() - started) * 1000

        started = perf_counter()
        features = rolling_features(frame, config["rolling_window"])
        model_candidate = (
            model.decision_function(features)
            < decisions["isolation_decision_threshold"]
        )
        model_prediction = persistence_mask(pd.Series(model_candidate), persistence).to_numpy()
        timings["isolation_forest"] += (perf_counter() - started) * 1000

        started = perf_counter()
        scored, _, _ = score(
            detect(
                frame,
                seed=config["model"]["random_state"],
                model=model,
                window=config["rolling_window"],
                isolation_threshold=decisions["isolation_decision_threshold"],
                thermal_temperature_threshold=decisions["thermal_temperature_threshold"],
                payload_temperature_threshold=decisions["payload_temperature_threshold"],
                battery_voltage_threshold=decisions["battery_voltage_threshold"],
                battery_current_threshold=decisions["battery_current_threshold"],
            ),
            persistence=persistence,
        )
        combined_prediction = scored.confirmed_combined_event.to_numpy(dtype=bool)
        timings["combined"] += (perf_counter() - started) * 1000

        if not np.array_equal(threshold_prediction, scored.confirmed_threshold_event.to_numpy()):
            raise RuntimeError("Threshold evaluation diverged from detector output")
        if not np.array_equal(model_prediction, scored.confirmed_model_event.to_numpy()):
            raise RuntimeError("Isolation Forest evaluation diverged from detector output")

        predictions["threshold"].append(threshold_prediction)
        predictions["isolation_forest"].append(model_prediction)
        predictions["combined"].append(combined_prediction)

    metrics = {
        method: calculate_metrics(truths, values, config["event_matching_tolerance"])
        for method, values in predictions.items()
    }
    for method, values in metrics.items():
        values["processing_time_ms"] = round(timings[method], 3)
        values["processing_time_scope"] = "Standalone test-run decision time; model fitting reported separately"
    return metrics, timings
def run_synthetic_evaluation(config: dict[str, Any]) -> dict[str, Any]:
    train_frames = [
        simulate("normal", config["observations"], seed)
        for seed in config["splits"]["train"]["normal_seeds"]
    ]
    fit_started = perf_counter()
    model = fit_isolation_forest(
        train_frames,
        seed=config["model"]["random_state"],
        window=config["rolling_window"],
        contamination=config["model"]["contamination"],
        n_estimators=config["model"]["n_estimators"],
    )
    fit_ms = (perf_counter() - fit_started) * 1000
    validation_metrics, _ = _evaluate_synthetic_runs(config["splits"]["validation"]["runs"], config, model)
    test_metrics, test_timings = _evaluate_synthetic_runs(config["splits"]["test"]["runs"], config, model)
    for method in ("isolation_forest", "combined"):
        test_metrics[method]["model_fit_time_ms"] = round(fit_ms, 3)
    return {
        "data_source": "ASTRA deterministic simulator",
        "dataset_version": config["dataset_version"],
        "configuration": config,
        "split_separation": {
            "train": config["splits"]["train"],
            "validation": config["splits"]["validation"],
            "test": config["splits"]["test"],
            "overlapping_seeds": False,
        },
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "test_processing_time_ms_by_method": {key: round(value, 3) for key, value in test_timings.items()},
    }


def _telemanom_features(values: np.ndarray, window: int) -> np.ndarray:
    primary = pd.Series(values[:, 0])
    rolling = primary.rolling(window, min_periods=1)
    temporal = np.column_stack([
        primary,
        rolling.mean(),
        rolling.std().fillna(0),
        primary.diff().fillna(0),
        (primary - primary.shift(window - 1)).fillna(0) / max(1, window - 1),
    ])
    return np.column_stack([temporal, values[:, 1:]])


def run_telemanom_evaluation(
    config: dict[str, Any], root: Path, mission: str,
    channels: list[str] | None = None, limit_channels: int | None = None,
) -> dict[str, Any]:
    selected = channels or available_channels(root, mission)
    if limit_channels is not None:
        selected = selected[:limit_channels]
    if not selected:
        raise ValueError(f"No {mission} channels selected")

    truths: list[np.ndarray] = []
    predictions = {method: [] for method in METHODS}
    timings = {method: 0.0 for method in METHODS}
    persistence = config["persistence_length"]
    model_config = config["model"]
    decision_threshold = config["decisions"]["isolation_decision_threshold"]

    def new_model() -> IsolationForest:
        return IsolationForest(
            n_estimators=model_config["n_estimators"],
            contamination=model_config["contamination"],
            random_state=model_config["random_state"],
            n_jobs=1,
        )

    for channel in selected:
        train, test = load_channel(root, channel)
        if test.mission != mission.upper():
            raise ValueError(f"Channel {channel} belongs to {test.mission}, not {mission}")
        train_values = train.frame[train.value_columns].to_numpy(dtype=float)
        test_values = test.frame[test.value_columns].to_numpy(dtype=float)
        truth = test.frame.ground_truth_anomaly.to_numpy(dtype=bool)
        truths.append(truth)

        started = perf_counter()
        primary = train_values[:, 0]
        median = float(np.median(primary))
        mad = float(np.median(np.abs(primary - median)))
        scale = max(1e-9, 1.4826 * mad)
        robust_candidate = (
            np.abs((test_values[:, 0] - median) / scale)
            > config["telemanom"]["robust_z_threshold"]
        )
        threshold_prediction = persistence_mask(
            pd.Series(robust_candidate), persistence,
        ).to_numpy()
        timings["threshold"] += (perf_counter() - started) * 1000

        started = perf_counter()
        train_features = _telemanom_features(train_values, config["rolling_window"])
        test_features = _telemanom_features(test_values, config["rolling_window"])
        model_candidate = (
            new_model().fit(train_features).decision_function(test_features)
            < decision_threshold
        )
        model_prediction = persistence_mask(
            pd.Series(model_candidate), persistence,
        ).to_numpy()
        timings["isolation_forest"] += (perf_counter() - started) * 1000

        started = perf_counter()
        combined_primary = train_values[:, 0]
        combined_median = float(np.median(combined_primary))
        combined_mad = float(np.median(np.abs(combined_primary - combined_median)))
        combined_scale = max(1e-9, 1.4826 * combined_mad)
        combined_robust = (
            np.abs((test_values[:, 0] - combined_median) / combined_scale)
            > config["telemanom"]["robust_z_threshold"]
        )
        combined_train_features = _telemanom_features(train_values, config["rolling_window"])
        combined_test_features = _telemanom_features(test_values, config["rolling_window"])
        combined_model = (
            new_model().fit(combined_train_features).decision_function(combined_test_features)
            < decision_threshold
        )
        combined_prediction = persistence_mask(
            pd.Series(combined_robust | combined_model), persistence,
        ).to_numpy()
        timings["combined"] += (perf_counter() - started) * 1000

        predictions["threshold"].append(threshold_prediction)
        predictions["isolation_forest"].append(model_prediction)
        predictions["combined"].append(combined_prediction)

    metrics = {
        method: calculate_metrics(truths, values, config["event_matching_tolerance"])
        for method, values in predictions.items()
    }
    for method, values in metrics.items():
        values["processing_time_ms"] = round(timings[method], 3)
        values["processing_time_scope"] = "Standalone end-to-end decision time including training for selected channels"
    return {
        "data_source": "Official Telemanom SMAP/MSL archive",
        "mission": mission.upper(),
        "channels": selected,
        "configuration": config,
        "original_train_test_separation_preserved": True,
        "test_metrics": metrics,
    }

def save_report(result: dict[str, Any], config_path: Path) -> None:
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    document = {
        "run_date_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _commit(),
        "config_path": str(config_path),
        **result,
    }
    slug = (
        f"telemanom_{str(document['mission']).lower()}"
        if document["data_source"].startswith("Official Telemanom")
        else "synthetic"
    )
    rows = [{"method": method, **metrics} for method, metrics in document["test_metrics"].items()]
    fieldnames = sorted({key for row in rows for key in row})

    for json_name, csv_name in (
        ("latest.json", "latest.csv"),
        (f"{slug}.json", f"{slug}.csv"),
    ):
        (REPORT_DIRECTORY / json_name).write_text(json.dumps(document, indent=2), encoding="utf-8")
        with (REPORT_DIRECTORY / csv_name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible ASTRA evaluations")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dataset", choices=("synthetic", "telemanom"), default="synthetic")
    parser.add_argument("--mission", choices=("SMAP", "MSL"), default="SMAP")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_TELEMANOM_ROOT)
    parser.add_argument("--channels", help="Comma-separated anonymized Telemanom channel IDs")
    parser.add_argument("--limit-channels", type=int)
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.dataset == "synthetic":
        result = run_synthetic_evaluation(config)
    else:
        selected = [item.strip() for item in args.channels.split(",")] if args.channels else None
        result = run_telemanom_evaluation(config, args.data_root, args.mission, selected, args.limit_channels)
    if not args.no_save:
        save_report(result, args.config)
    print(json.dumps(result["test_metrics"], indent=2))


if __name__ == "__main__":
    main()




