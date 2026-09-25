from dataclasses import dataclass, field
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "observation_index",
    "timestamp",
    "ground_truth_anomaly",
    "ground_truth_event_id",
}


@dataclass
class TelemetryRun:
    source_name: str
    dataset_family: str
    mission: str
    channel_id: str
    split: str
    frame: pd.DataFrame
    value_columns: list[str]
    scenario: str | None = None
    units: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "TelemetryRun":
        missing = REQUIRED_COLUMNS - set(self.frame.columns)
        if missing:
            raise ValueError(f"Canonical telemetry is missing columns: {sorted(missing)}")
        if self.frame.observation_index.duplicated().any():
            raise ValueError("observation_index values must be unique")
        if not self.value_columns or any(column not in self.frame for column in self.value_columns):
            raise ValueError("value_columns must name existing telemetry columns")
        if not pd.api.types.is_bool_dtype(self.frame.ground_truth_anomaly):
            raise ValueError("ground_truth_anomaly must be boolean")
        return self
