# ASTRA technical facts

## Architecture

- FastAPI/Pydantic API with deterministic NumPy/Pandas simulation and scikit-learn Isolation Forest.
- Vite/React browser dashboard with Recharts and Lucide React.
- One batch `POST /api/simulate` returns 180 observations; the browser progressively reveals that response as a simulated replay.
- No database, authentication, message queue, WebSocket, spacecraft link or command path exists.

## Detection and evidence

- **Simulated telemetry demonstration:** fixed operating thresholds plus Isolation Forest only when thermal or power trends corroborate it, followed by three consecutive candidate observations for confirmation.
- **Public telemetry research evaluation:** offline Telemanom SMAP/MSL comparison of robust threshold, Isolation Forest and combined methods.
- **Phase 1C recommendation:** robust threshold baseline. The frozen configuration hash is `1749b3b56198cf9d3f016a2c690354e2f48cf5d39b4e8810fa59fbfb2e7f46e2`.
- **Planned mission integration:** future work requiring mission-specific limits, interfaces and qualification.

## Data and evaluation design

- Simulator values are explicitly labelled synthetic telemetry with deterministic seeds.
- Public source: 81 anonymized, pre-scaled Telemanom SMAP/MSL channels.
- Phase 1C used 6 previously viewed development channels and a frozen 20-channel unseen holdout.
- Training-array chronological splits and separately labelled synthetic ramps were used for calibration; public test labels were withheld until the frozen holdout evaluation.
- Current backend suite: 37 tests before Phase 3 changes; the release verification result is recorded in `RELEASE_CHECKLIST.md`.

## Phase 1C holdout metrics

| Method | Micro F1 | Macro F1 | Event recall | Point FPR | False alerts/1,000 |
|---|---:|---:|---:|---:|---:|
| Threshold | 0.328218 | 0.139126 | 0.461538 | 0.177143 | 1.693267 |
| Isolation Forest | 0.220356 | 0.111960 | 0.384615 | 0.074910 | 3.647729 |
| Combined | 0.347309 | 0.179961 | 0.500000 | 0.182397 | 2.413806 |

The combined method improved aggregate F1 and event recall while increasing false alerts. It did not satisfy the predeclared selection rule, so the simpler threshold baseline remains recommended.

## Bundle review

The pre-hardening production JavaScript bundle was 613.30 kB (182.31 kB gzip), with a Vite chunk-size warning. A Rollup module contribution inspection identified Recharts and its charting dependencies as the main rendered contribution; Lucide's large installed source tree is tree-shaken to imported icons. Charting is primary dashboard content, so deferring it would hide the core telemetry view and only move the warning into another chunk. The Phase 3 changes keep one predictable bundle rather than add risky loading states. Final build size is recorded in `RELEASE_CHECKLIST.md`.

## Limitations

- Public telemetry is anonymized and pre-scaled; physical units and exact mission timestamps are unavailable.
- Public-data metrics are an initial benchmark, not operational validation.
- Simulator results do not prove mission generalization.
- Risk and health scores are prototype heuristic indicators, not failure probabilities.
- Alert explanations are anomaly evidence, not confirmed diagnosis.
- Analysis time covers backend model execution and excludes spacecraft transmission time.
- Event notes and review state exist only in current browser memory; exports are local prototype reports.

## Unsupported claims

Avoid: predictive maintenance, failure prediction, live spacecraft data, autonomous control, confirmed root-cause diagnosis, proven accuracy, NASA validation and operational readiness. No LSTM or other deep-learning model is implemented.
