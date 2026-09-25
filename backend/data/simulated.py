import pandas as pd

from .base import TelemetryRun
from ..simulator import CHANNELS, UNITS, simulate


SIMULATOR_VERSION = "astra-simulator-v1"


def load_simulated_run(scenario: str, points: int, seed: int, split: str) -> TelemetryRun:
    source = simulate(scenario, points, seed)
    canonical = pd.DataFrame({
        "observation_index": range(len(source)),
        "timestamp": source.timestamp,
        "ground_truth_anomaly": source.fault_active.astype(bool),
        "ground_truth_event_id": source.ground_truth_event_id,
    })
    for channel in CHANNELS:
        canonical[channel] = source[channel].astype(float)
    return TelemetryRun(
        source_name="ASTRA deterministic simulator",
        dataset_family="ASTRA simulator",
        mission="ASTRA-01 synthetic",
        channel_id="multisystem",
        split=split,
        scenario=scenario,
        frame=canonical,
        value_columns=list(CHANNELS),
        units=dict(UNITS),
        provenance={"simulator_version": SIMULATOR_VERSION, "seed": seed, "points": points},
    ).validate()
