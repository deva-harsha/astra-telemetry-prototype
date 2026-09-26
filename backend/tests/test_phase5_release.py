import hashlib
import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports" / "evaluation"
EVIDENCE_PATH = ROOT / "frontend" / "src" / "validationEvidence.json"

FROZEN_HASHES = {
    "phase1c_holdout_results.json": "dd8fb1d354dd50a2314f15eabed9972e3c756857c6a23d9330e28de9b33d610a",
    "phase1c_holdout_manifest.json": "62171032a6c1812a4098927abf33ef3dbaad2087226f5997fa7b0d02b59e50dc",
    "phase4_lstm_holdout_results.json": "4380d64c8bc1d38bf61b50bd09edbbf1bc4901f5c79ee9832cd267d452ccac73",
    "phase4_lstm_holdout_manifest.json": "f85ee071d38a8330ebaf22febe3acb6ae73c0f2760b17867c43d69d55c0a6dea",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_frozen_phase1c_and_phase4_evidence_files_are_unchanged():
    for filename, expected_hash in FROZEN_HASHES.items():
        actual_hash = hashlib.sha256((REPORTS / filename).read_bytes()).hexdigest()
        assert actual_hash == expected_hash


def test_frontend_evidence_matches_both_frozen_reports():
    evidence = load_json(EVIDENCE_PATH)
    phase1 = load_json(REPORTS / "phase1c_holdout_results.json")
    phase4 = load_json(REPORTS / "phase4_lstm_holdout_results.json")

    for item in evidence["phase1c"]["methods"]:
        key = {"Threshold": "threshold", "Isolation Forest": "isolation_forest", "Combined": "combined"}[item["method"]]
        assert item["micro_f1"] == phase1["micro"][key]["point_f1"]
        assert item["macro_f1"] == phase1["macro"][key]["point_f1"]
        assert item["event_recall"] == phase1["micro"][key]["event_recall"]
        assert item["point_fpr"] == phase1["micro"][key]["point_false_positive_rate"]
        assert item["false_alerts_per_1000"] == phase1["micro"][key]["false_alerts_per_1000_observations"]

    method_keys = {
        "Threshold": "threshold",
        "Isolation Forest": "isolation_forest",
        "Combined": "combined",
        "LSTM Autoencoder": "lstm_autoencoder",
    }
    for item in evidence["phase4"]["methods"]:
        key = method_keys[item["method"]]
        assert item["macro_f1"] == phase4["macro"][key]["point_f1"]
        assert item["event_recall"] == phase4["micro"][key]["event_recall"]
        assert item["false_alerts_per_1000"] == phase4["micro"][key]["false_alerts_per_1000_observations"]
        assert item["median_delay"] == phase4["detection_delay_distribution"][key]["median"]

    reported_gates = phase4["phase5_eligibility_gate"]
    assert {gate["key"]: gate["passed"] for gate in evidence["phase4"]["gates"]} == reported_gates["checks"]
    assert evidence["phase4"]["overall_passed"] is reported_gates["passed"]
    assert evidence["phase4"]["experiment"]["frozen_configuration"] == phase4["frozen_configuration"]["configuration_sha256"]


def test_production_backend_imports_when_torch_is_unavailable():
    command = (
        "import importlib.util, sys; "
        "assert importlib.util.find_spec('torch') is None; "
        "import backend.main; "
        "assert 'torch' not in sys.modules; "
        "assert 'backend.evaluation.lstm_autoencoder' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_normal_simulation_release_contract_is_unchanged():
    response = TestClient(app).post("/api/simulate", json={"scenario": "normal", "points": 180, "seed": 42})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["telemetry"]) == 180
    assert payload["event"] is None
    assert payload["events"] == []
    assert payload["metrics"]["detected_event_count"] == 0
