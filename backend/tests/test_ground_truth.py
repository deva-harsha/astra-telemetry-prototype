from backend.simulator import simulate


def test_normal_has_no_injected_fault():
    frame = simulate("normal", 180, 42)
    assert not frame.fault_active.any()
    assert frame.ground_truth_event_id.isna().all()
    assert frame.fault_type.isna().all()


def test_thermal_and_power_fault_ground_truth_starts_at_documented_index():
    for scenario, subsystem in (("thermal_fault", "Thermal"), ("power_fault", "Power")):
        frame = simulate(scenario, 180, 42)
        onset = 108
        assert not frame.iloc[onset - 1].fault_active
        assert frame.iloc[onset].fault_active
        assert frame.iloc[onset].fault_start_index == onset
        assert frame.iloc[onset].injected_subsystem == subsystem
        assert frame.iloc[onset].ground_truth_event_id == f"{scenario}-1"


def test_ground_truth_is_deterministic_and_separate_from_detector_output():
    first = simulate("thermal_fault", 180, 7)
    second = simulate("thermal_fault", 180, 7)
    assert first.fault_start_timestamp.tolist() == second.fault_start_timestamp.tolist()
    assert first.fault_active.tolist() == second.fault_active.tolist()
    assert "is_anomaly" not in first.columns

from backend.data.simulated import load_simulated_run


def test_simulator_uses_canonical_telemetry_contract():
    run = load_simulated_run("power_fault", 60, 9, "test")
    assert run.source_name == "ASTRA deterministic simulator"
    assert run.split == "test"
    assert run.frame.observation_index.tolist() == list(range(60))
    assert run.frame.ground_truth_anomaly.dtype == bool
