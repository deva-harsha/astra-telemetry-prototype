import ast
import csv
from pathlib import Path

import numpy as np
import pandas as pd

from .base import TelemetryRun


class TelemanomDataError(ValueError):
    pass


def parse_anomaly_ranges(value: str, length: int | None = None) -> list[tuple[int, int]]:
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise TelemanomDataError(f"Malformed anomaly range: {value!r}") from exc
    if not isinstance(parsed, list):
        raise TelemanomDataError("anomaly_sequences must be a list")
    ranges: list[tuple[int, int]] = []
    for item in parsed:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise TelemanomDataError(f"Invalid anomaly interval: {item!r}")
        start, end = item
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
            raise TelemanomDataError(f"Invalid anomaly interval: {item!r}")
        if length is not None and end >= length:
            raise TelemanomDataError(f"Anomaly interval {item!r} exceeds sequence length {length}")
        ranges.append((start, end))
    return ranges


def _find_data_root(root: Path) -> Path:
    candidates = [root, root / "data"]
    candidates.extend(path.parent for path in root.rglob("train") if path.is_dir())
    for candidate in candidates:
        if (candidate / "train").is_dir() and (candidate / "test").is_dir():
            return candidate
    raise FileNotFoundError(f"Telemanom train/ and test/ directories were not found under {root}")


def _labels_path(root: Path, data_root: Path) -> Path:
    for path in (root / "labeled_anomalies.csv", data_root / "labeled_anomalies.csv"):
        if path.is_file():
            return path
    matches = list(root.rglob("labeled_anomalies.csv"))
    if matches:
        return matches[0]
    raise FileNotFoundError("labeled_anomalies.csv is missing")


def read_labels(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = {"chan_id", "spacecraft", "anomaly_sequences"}
    if not rows or not required.issubset(rows[0]):
        raise TelemanomDataError(f"{path} must contain columns {sorted(required)}")
    return rows


def available_channels(root: Path, mission: str | None = None) -> list[str]:
    data_root = _find_data_root(root)
    rows = read_labels(_labels_path(root, data_root))
    return sorted({
        row["chan_id"] for row in rows
        if mission is None or row["spacecraft"].upper() == mission.upper()
    })


def load_channel(root: Path, channel_id: str) -> tuple[TelemetryRun, TelemetryRun]:
    root = Path(root)
    data_root = _find_data_root(root)
    train_path = data_root / "train" / f"{channel_id}.npy"
    test_path = data_root / "test" / f"{channel_id}.npy"
    if not train_path.is_file() or not test_path.is_file():
        raise FileNotFoundError(f"Missing train/test .npy files for channel {channel_id}")

    train = np.load(train_path, allow_pickle=False)
    test = np.load(test_path, allow_pickle=False)
    if train.ndim != 2 or test.ndim != 2 or train.shape[1] != test.shape[1] or train.shape[1] < 1:
        raise TelemanomDataError(f"Channel {channel_id} arrays must be 2-D with matching feature counts")

    rows = [row for row in read_labels(_labels_path(root, data_root)) if row["chan_id"] == channel_id]
    if not rows:
        raise TelemanomDataError(f"No label metadata found for channel {channel_id}")
    mission = rows[0]["spacecraft"].upper()
    labels = np.zeros(len(test), dtype=bool)
    event_ids: list[str | None] = [None] * len(test)
    event_number = 0
    for row in rows:
        for start, end in parse_anomaly_ranges(row["anomaly_sequences"], len(test)):
            event_number += 1
            labels[start:end + 1] = True
            for index in range(start, end + 1):
                event_ids[index] = f"{channel_id}-{event_number}"

    def build(values: np.ndarray, split: str, truth: np.ndarray, ids: list[str | None]) -> TelemetryRun:
        columns = [f"value_{i}" for i in range(values.shape[1])]
        frame = pd.DataFrame(values, columns=columns)
        frame.insert(0, "ground_truth_event_id", ids)
        frame.insert(0, "ground_truth_anomaly", truth.astype(bool))
        frame.insert(0, "timestamp", [None] * len(values))
        frame.insert(0, "observation_index", range(len(values)))
        return TelemetryRun(
            source_name="Official Telemanom SMAP/MSL archive",
            dataset_family="Telemanom",
            mission=mission,
            channel_id=channel_id,
            split=split,
            frame=frame,
            value_columns=columns,
            units={},
            provenance={
                "repository": "https://github.com/khundman/telemanom",
                "distribution": "Downloaded from a source documented by the official Telemanom repository",
                "labels": "labeled_anomalies.csv",
                "anonymized": True,
                "pre_scaled": True,
            },
        ).validate()

    return (
        build(train, "train", np.zeros(len(train), dtype=bool), [None] * len(train)),
        build(test, "test", labels, event_ids),
    )

