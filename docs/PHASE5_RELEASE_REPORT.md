# ASTRA Phase 5 release report

## Decision

The Phase 4 PyTorch LSTM Autoencoder remains offline research evidence. It is not part of the live simulation API, detector controls, production requirements or deployment artifact.

ASTRA implemented and evaluated an LSTM Autoencoder. It reduced false alerts, but missed more real anomaly events and detected matched events later. Because it failed the predeclared acceptance gate, it was not integrated into the live prototype.

## Evidence integration

Validation Evidence now separates Phase 1C Public Baseline Evaluation (20-channel frozen holdout) and Phase 4 Deep Learning Experiment (nine-channel frozen holdout). The interface warns that values must be interpreted within each experiment. Phase 4 shows exact same-holdout metrics, five checks, the failed overall decision and the non-integration rationale.

## Deployment isolation

- Render installs only backend/requirements.txt.
- backend/requirements.txt has no torch dependency.
- backend/requirements-dl.txt is an offline experiment add-on.
- Normal FastAPI startup imports no PyTorch or Phase 4 model module.
- .venv-dl, artifacts/models, .pt and .pth files are ignored.
- The frontend and production API do not load the trained model artifact.

## Product truth

### Live prototype

React, Vite, Recharts, FastAPI, Uvicorn, Python, scikit-learn Isolation Forest, fixed operating thresholds, trend corroboration, three-observation persistence and simulated multi-subsystem telemetry.

### Offline research evaluation

Public Telemanom SMAP/MSL telemetry, robust threshold, Isolation Forest, combined detection, PyTorch LSTM Autoencoder, frozen splits and precision, recall, F1, false-alert and detection-delay metrics.

Deep learning evaluated, not blindly deployed. ASTRA selects models based on measured mission-safety trade-offs rather than model complexity.

## Release boundary

This is a ground-based decision-support prototype. It does not communicate with or control a spacecraft, predict exact failure time, confirm root cause, provide operational validation or claim endorsement by a space agency.
