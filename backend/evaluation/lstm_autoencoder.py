"""Leakage-safe utilities for the optional Phase 4 LSTM autoencoder experiment.

This module deliberately imports PyTorch only inside framework-specific functions so
base ASTRA tests and production imports do not require the optional dependency.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SequenceBatch:
    windows: np.ndarray
    end_indices: np.ndarray
    boundary_ids: np.ndarray


def make_sequences(
    values: np.ndarray,
    window_size: int,
    *,
    stride: int = 1,
    boundary_ids: np.ndarray | None = None,
) -> SequenceBatch:
    """Create chronological windows and align each window to its final observation."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError("values must be a two-dimensional array")
    if window_size < 2 or stride < 1:
        raise ValueError("window_size must be >= 2 and stride must be >= 1")
    boundaries = np.asarray(boundary_ids if boundary_ids is not None else np.zeros(len(values), dtype=int))
    if boundaries.shape != (len(values),):
        raise ValueError("boundary_ids must have one entry per observation")
    windows: list[np.ndarray] = []
    ends: list[int] = []
    ids: list[Any] = []
    for end in range(window_size - 1, len(values), stride):
        start = end - window_size + 1
        segment_ids = boundaries[start:end + 1]
        if np.all(segment_ids == segment_ids[0]):
            windows.append(values[start:end + 1])
            ends.append(end)
            ids.append(segment_ids[0])
    shape = (0, window_size, values.shape[1])
    return SequenceBatch(
        np.asarray(windows, dtype=np.float32) if windows else np.empty(shape, dtype=np.float32),
        np.asarray(ends, dtype=int),
        np.asarray(ids),
    )


@dataclass
class TrainOnlyRobustScaler:
    epsilon: float = 1e-8
    feature_names: list[str] | None = None
    impute_: np.ndarray | None = None
    center_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    retained_: np.ndarray | None = None

    def fit(self, values: np.ndarray, feature_names: list[str] | None = None) -> "TrainOnlyRobustScaler":
        values = np.asarray(values, dtype=float)
        if values.ndim != 2 or len(values) < 2:
            raise ValueError("fit values must be a two-dimensional array with at least two rows")
        with np.errstate(all="ignore"):
            impute = np.nanmedian(values, axis=0)
        impute = np.where(np.isfinite(impute), impute, 0.0)
        filled = np.where(np.isfinite(values), values, impute)
        center = np.median(filled, axis=0)
        mad = 1.4826 * np.median(np.abs(filled - center), axis=0)
        std = np.std(filled, axis=0)
        retained = np.maximum(mad, std) > self.epsilon
        if not np.any(retained):
            raise ValueError("all selected features are constant in fitting data")
        names = feature_names or [f"value_{index}" for index in range(values.shape[1])]
        if len(names) != values.shape[1]:
            raise ValueError("feature_names length does not match values")
        self.feature_names = list(names)
        self.impute_ = impute
        self.center_ = center
        self.scale_ = np.where(mad > self.epsilon, mad, np.maximum(std, self.epsilon))
        self.retained_ = retained
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if self.impute_ is None or self.center_ is None or self.scale_ is None or self.retained_ is None:
            raise RuntimeError("scaler must be fitted before transform")
        values = np.asarray(values, dtype=float)
        if values.ndim != 2 or values.shape[1] != len(self.impute_):
            raise ValueError("transform values have incompatible dimensions")
        filled = np.where(np.isfinite(values), values, self.impute_)
        return ((filled - self.center_) / self.scale_)[:, self.retained_]

    @property
    def retained_features(self) -> list[str]:
        if self.feature_names is None or self.retained_ is None:
            raise RuntimeError("scaler must be fitted before inspecting features")
        return [name for name, keep in zip(self.feature_names, self.retained_, strict=True) if keep]

    @property
    def removed_features(self) -> list[str]:
        if self.feature_names is None or self.retained_ is None:
            raise RuntimeError("scaler must be fitted before inspecting features")
        return [name for name, keep in zip(self.feature_names, self.retained_, strict=True) if not keep]


def validation_threshold(errors: np.ndarray, quantile: float) -> float:
    values = np.asarray(errors, dtype=float)
    values = values[np.isfinite(values)]
    if not 0.5 < quantile < 1.0:
        raise ValueError("threshold quantile must be between 0.5 and 1.0")
    if not len(values):
        raise ValueError("at least one finite validation error is required")
    return float(np.quantile(values, quantile))


def align_window_scores(scores: np.ndarray, end_indices: np.ndarray, observation_count: int) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    ends = np.asarray(end_indices, dtype=int)
    if scores.shape != ends.shape:
        raise ValueError("scores and end_indices must have identical shapes")
    if np.any(ends < 0) or np.any(ends >= observation_count) or len(np.unique(ends)) != len(ends):
        raise ValueError("end_indices must be unique valid observation positions")
    aligned = np.full(observation_count, np.nan, dtype=float)
    aligned[ends] = scores
    return aligned


def persistence_decision(candidates: np.ndarray, length: int) -> np.ndarray:
    if length < 1:
        raise ValueError("persistence length must be positive")
    streak = 0
    result = np.zeros(len(candidates), dtype=bool)
    for index, value in enumerate(np.asarray(candidates, dtype=bool)):
        streak = streak + 1 if value else 0
        result[index] = streak >= length
    return result


def mean_per_feature_error(windows: np.ndarray, reconstructions: np.ndarray) -> np.ndarray:
    original = np.asarray(windows, dtype=float)
    rebuilt = np.asarray(reconstructions, dtype=float)
    if original.shape != rebuilt.shape or original.ndim != 3:
        raise ValueError("windows and reconstructions must have the same three-dimensional shape")
    return np.mean(np.abs(original - rebuilt), axis=(0, 1))


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def configuration_hash(config: dict[str, Any]) -> str:
    payload = {key: value for key, value in config.items() if key != "configuration_sha256"}
    encoded = json.dumps(json_safe(payload), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def freeze_configuration(config: dict[str, Any]) -> dict[str, Any]:
    frozen = json.loads(json.dumps(json_safe(config)))
    frozen["frozen"] = True
    frozen["configuration_sha256"] = configuration_hash(frozen)
    return frozen


def verify_frozen_configuration(config: dict[str, Any]) -> None:
    if not config.get("frozen"):
        raise ValueError("configuration is not frozen")
    if config.get("configuration_sha256") != configuration_hash(config):
        raise ValueError("frozen configuration hash mismatch")


def select_unseen_holdout(
    available: dict[str, list[str]],
    excluded: dict[str, list[str]],
    *,
    requested_per_mission: int,
    salt: str,
) -> tuple[dict[str, list[str]], list[str]]:
    selected: dict[str, list[str]] = {}
    limitations: list[str] = []
    for mission in sorted(available):
        excluded_set = set(excluded.get(mission, []))
        candidates = [channel for channel in available[mission] if channel not in excluded_set]
        ranked = sorted(candidates, key=lambda channel: hashlib.sha256(f"{salt}:{mission}:{channel}".encode()).hexdigest())
        count = min(requested_per_mission, len(ranked))
        selected[mission] = ranked[:count]
        if count < requested_per_mission:
            limitations.append(f"{mission} has only {count} valid unseen channels after required exclusions; requested {requested_per_mission}.")
    return selected, limitations


def set_deterministic_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
    except ImportError:
        return
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def _torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError("PyTorch is optional. Run this experiment inside .venv-dl.") from exc
    return torch, nn


def build_model(input_size: int, latent_units: int, layers: int):
    torch, nn = _torch()

    class LstmAutoencoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.LSTM(input_size, latent_units, num_layers=layers, batch_first=True)
            self.decoder = nn.LSTM(latent_units, latent_units, num_layers=layers, batch_first=True)
            self.output = nn.Linear(latent_units, input_size)

        def forward(self, values):
            _, (hidden, _) = self.encoder(values)
            latent = hidden[-1]
            repeated = latent.unsqueeze(1).repeat(1, values.shape[1], 1)
            decoded, _ = self.decoder(repeated)
            return self.output(decoded)

    return LstmAutoencoder().to(torch.device("cpu"))


def train_autoencoder(
    train_windows: np.ndarray,
    validation_windows: np.ndarray,
    config: dict[str, Any],
):
    torch, nn = _torch()
    set_deterministic_seeds(int(config["random_seed"]))
    if train_windows.ndim != 3 or validation_windows.ndim != 3 or train_windows.shape[2] != validation_windows.shape[2]:
        raise ValueError("training and validation windows must be compatible three-dimensional arrays")
    model = build_model(train_windows.shape[2], int(config["latent_units"]), int(config["lstm_layers"]))
    loss_fn = nn.L1Loss() if config["loss"] == "mae" else nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=float(config["learning_rate"]))
    batch_size = int(config["batch_size"])
    patience = int(config["early_stopping_patience"])
    best_loss = float("inf")
    best_state = None
    stale = 0
    history: list[dict[str, float | int]] = []
    train_tensor = torch.as_tensor(train_windows, dtype=torch.float32)
    validation_tensor = torch.as_tensor(validation_windows, dtype=torch.float32)
    for epoch in range(1, int(config["max_epochs"]) + 1):
        model.train()
        losses: list[float] = []
        for start in range(0, len(train_tensor), batch_size):
            batch = train_tensor[start:start + batch_size]
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch), batch)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            validation_loss = float(loss_fn(model(validation_tensor), validation_tensor))
        history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "validation_loss": validation_loss})
        if validation_loss < best_loss - float(config["early_stopping_min_delta"]):
            best_loss = validation_loss
            best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                break
    if best_state is None:
        raise RuntimeError("training did not produce a model state")
    model.load_state_dict(best_state)
    model.eval()
    return model, history


def reconstruction_errors(model, windows: np.ndarray, batch_size: int = 256) -> tuple[np.ndarray, np.ndarray]:
    torch, _ = _torch()
    tensor = torch.as_tensor(windows, dtype=torch.float32)
    sample_errors: list[np.ndarray] = []
    feature_error_sum = np.zeros(windows.shape[2], dtype=float)
    observed = 0
    model.eval()
    with torch.no_grad():
        for start in range(0, len(tensor), batch_size):
            batch = tensor[start:start + batch_size]
            rebuilt = model(batch)
            absolute = torch.abs(rebuilt - batch)
            sample_errors.append(absolute.mean(dim=(1, 2)).cpu().numpy())
            feature_error_sum += absolute.sum(dim=(0, 1)).cpu().numpy()
            observed += batch.shape[0] * batch.shape[1]
    errors = np.concatenate(sample_errors) if sample_errors else np.empty(0, dtype=float)
    return errors, feature_error_sum / max(1, observed)


def save_model_artifact(model, path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    torch, _ = _torch()
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "metadata": json_safe(metadata)}, path)
    payload = path.read_bytes()
    return {"path": str(path), "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
