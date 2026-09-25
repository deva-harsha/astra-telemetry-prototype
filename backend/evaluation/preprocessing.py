from dataclasses import dataclass

import numpy as np
import pandas as pd


FEATURE_SETS = {
    "raw": ("raw", "missing"),
    "rolling": ("raw", "rolling_mean", "rolling_std", "rolling_slope", "missing"),
    "difference": ("raw", "difference", "missing"),
    "combined": (
        "raw", "difference", "rolling_mean", "rolling_std", "rolling_slope", "missing",
    ),
}


def chronological_split(values: np.ndarray, fit_fraction: float = 0.7) -> tuple[np.ndarray, np.ndarray]:
    if not 0.5 <= fit_fraction < 1.0:
        raise ValueError("fit_fraction must be in [0.5, 1.0)")
    cut = max(2, min(len(values) - 1, int(len(values) * fit_fraction)))
    return values[:cut], values[cut:]


def _feature_frame(
    values: np.ndarray, feature_set: str, window: int, history: np.ndarray | None = None,
) -> pd.DataFrame:
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature set: {feature_set}")
    primary = np.asarray(values, dtype=float)[:, 0]
    prefix = np.asarray(history, dtype=float)[:, 0] if history is not None and len(history) else np.array([])
    series = pd.Series(np.concatenate([prefix, primary]))
    rolling = series.rolling(window, min_periods=1)
    frame = pd.DataFrame({
        "raw": series,
        "difference": series.diff(),
        "rolling_mean": rolling.mean(),
        "rolling_std": rolling.std(ddof=0),
        "rolling_slope": (series - series.shift(window - 1)) / max(1, window - 1),
        "missing": series.isna().astype(float),
    }).iloc[len(prefix):].reset_index(drop=True)
    return frame.loc[:, FEATURE_SETS[feature_set]]


@dataclass
class RobustFeatureScaler:
    feature_set: str = "combined"
    window: int = 5
    near_constant_epsilon: float = 1e-8
    columns_: list[str] | None = None
    impute_: np.ndarray | None = None
    center_: np.ndarray | None = None
    scale_: np.ndarray | None = None
    retained_: np.ndarray | None = None

    def fit(self, values: np.ndarray) -> "RobustFeatureScaler":
        frame = _feature_frame(values, self.feature_set, self.window)
        raw = frame.to_numpy(dtype=float)
        with np.errstate(all="ignore"):
            impute = np.nanmedian(raw, axis=0)
        impute = np.where(np.isfinite(impute), impute, 0.0)
        filled = np.where(np.isfinite(raw), raw, impute)
        center = np.median(filled, axis=0)
        mad_scale = 1.4826 * np.median(np.abs(filled - center), axis=0)
        std = np.std(filled, axis=0)
        self.columns_ = list(frame.columns)
        self.impute_ = impute
        self.center_ = center
        self.scale_ = np.where(mad_scale > self.near_constant_epsilon, mad_scale, np.maximum(std, 1.0))
        variable = np.maximum(mad_scale, std) > self.near_constant_epsilon
        # Keep this binary indicator so missingness first seen after fitting remains observable.
        self.retained_ = variable | (np.asarray(self.columns_) == "missing")
        return self

    def transform(self, values: np.ndarray, history: np.ndarray | None = None) -> np.ndarray:
        if self.retained_ is None or self.impute_ is None or self.center_ is None or self.scale_ is None:
            raise RuntimeError("Scaler must be fitted before transform")
        raw = _feature_frame(values, self.feature_set, self.window, history).to_numpy(dtype=float)
        filled = np.where(np.isfinite(raw), raw, self.impute_)
        return ((filled - self.center_) / self.scale_)[:, self.retained_]

    @property
    def retained_columns(self) -> list[str]:
        if self.columns_ is None or self.retained_ is None:
            raise RuntimeError("Scaler must be fitted before inspecting columns")
        return [name for name, keep in zip(self.columns_, self.retained_, strict=True) if keep]

    @property
    def removed_columns(self) -> list[str]:
        if self.columns_ is None or self.retained_ is None:
            raise RuntimeError("Scaler must be fitted before inspecting columns")
        return [name for name, keep in zip(self.columns_, self.retained_, strict=True) if not keep]

    def primary_robust_score(self, values: np.ndarray) -> np.ndarray:
        if self.impute_ is None or self.center_ is None or self.scale_ is None:
            raise RuntimeError("Scaler must be fitted before scoring")
        primary = np.asarray(values, dtype=float)[:, 0]
        filled = np.where(np.isfinite(primary), primary, self.impute_[0])
        return np.abs((filled - self.center_[0]) / max(self.scale_[0], self.near_constant_epsilon))
