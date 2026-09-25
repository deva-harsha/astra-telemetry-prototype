from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .schemas import Scenario


CHANNELS = (
    "battery_voltage",
    "battery_current",
    "battery_temperature",
    "signal_strength",
    "attitude_error",
    "payload_temperature",
    "propulsion_pressure",
    "radiation_level",
)

UNITS = {
    "battery_voltage": "V",
    "battery_current": "A",
    "battery_temperature": "°C",
    "signal_strength": "dBm",
    "attitude_error": "degrees",
    "payload_temperature": "°C",
    "propulsion_pressure": "kPa",
    "radiation_level": "mGy/h",
}


def simulate(scenario: Scenario, points: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(points, dtype=float)
    wave = np.sin(t / 18)
    data = {
        "battery_voltage": 28.2 + 0.08 * wave + rng.normal(0, 0.055, points),
        "battery_current": 2.15 + 0.06 * np.sin(t / 11) + rng.normal(0, 0.055, points),
        "battery_temperature": 22.2 + 0.28 * wave + rng.normal(0, 0.16, points),
        "signal_strength": -83 + 0.45 * wave + rng.normal(0, 0.38, points),
        "attitude_error": np.clip(0.16 + rng.normal(0, 0.035, points), 0, None),
        "payload_temperature": 25.0 + 0.3 * np.sin(t / 20) + rng.normal(0, 0.18, points),
        "propulsion_pressure": 210 + 0.4 * wave + rng.normal(0, 0.45, points),
        "radiation_level": np.clip(0.12 + rng.normal(0, 0.009, points), 0, None),
    }
    onset = int(points * 0.6)
    progress = np.clip((t - onset) / max(1, points - onset - 1), 0, 1)
    if scenario == "thermal_fault":
        data["battery_temperature"] += 18 * progress
        data["payload_temperature"] += 17 * progress
    elif scenario == "power_fault":
        data["battery_voltage"] -= 4.7 * progress
        data["battery_current"] += 2.2 * progress + rng.normal(0, 0.12, points) * progress
        data["battery_temperature"] += 10 * progress

    start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    frame = pd.DataFrame(data)
    frame.insert(0, "timestamp", [start + timedelta(minutes=i) for i in range(points)])
    has_fault = scenario != "normal"
    fault_start = start + timedelta(minutes=onset) if has_fault else None
    frame["fault_active"] = has_fault & (frame.index >= onset)
    frame["fault_type"] = scenario if has_fault else None
    frame["injected_subsystem"] = (
        "Thermal" if scenario == "thermal_fault" else "Power" if scenario == "power_fault" else None
    )
    frame["fault_start_index"] = onset if has_fault else None
    frame["fault_start_timestamp"] = fault_start
    frame["ground_truth_event_id"] = [f"{scenario}-1" if has_fault and i >= onset else None for i in range(points)]
    return frame
