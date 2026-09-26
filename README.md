# ASTRA

ASTRA is a ground-based spacecraft telemetry decision-support prototype that detects persistent unusual behaviour, connects supporting signal evidence and helps operators investigate confirmed events.

It does not connect to or control a spacecraft, predict a failure or exact failure time, confirm a root-cause diagnosis, or claim agency endorsement or operational validation.

## Reproducible Python 3.12 environment

Use a separate environment without deleting the existing environments:

~~~powershell
cd C:\ASTRA
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install --upgrade pip
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv312\Scripts\python.exe -m pytest backend\tests -q
~~~

On this workstation, Windows policy denies the Microsoft Store Python launcher. The following verified fallback uses the existing permitted bundled Python 3.12 runtime:

~~~powershell
cd C:\ASTRA
& 'C:\Users\vbitr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
~~~

The import smoke test in backend/tests/test_imports.py verifies NumPy, Pandas, SciPy, scikit-learn, FastAPI and the ASTRA application. Do not disable Windows Application Control if another environment is blocked.

## Current demonstration

Start the backend:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
~~~

Start the frontend:

~~~powershell
cd C:\ASTRA\frontend
npm ci
npm run dev -- --host localhost --port 5173
~~~

Open http://localhost:5173. API documentation is at http://127.0.0.1:8000/docs.

The browser requests all 180 observations in one POST to /api/simulate. The backend generates deterministic telemetry, fits the live-demo detector to the initial normal segment, scores the complete batch, and returns it. The browser then progressively reveals the completed response as a replay. Pause and playback speed affect only this browser replay.

The response remains backward compatible and adds explicit injected-fault ground truth, fault-onset metadata, and an alert-confirmation timestamp. Detector decisions remain separate from ground truth.

## Evaluation

Run the independent synthetic benchmark:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m backend.evaluation.run --config backend\evaluation\configs\default.json
~~~

The versioned configuration uses multiple normal training seeds, separate validation seeds, and different held-out test seeds. Seeds cannot overlap. It evaluates these decisions separately:

- **Threshold baseline:** fixed simulator operating limits.
- **Isolation Forest:** an unsupervised model trained only on independent normal runs.
- **Combined ASTRA decision:** the existing threshold plus model/trend policy.
- **Persistence rule:** an alert is confirmed only after three consecutive candidate observations.

Successful runs write JSON and CSV reports under reports/evaluation. The executed Phase 1 evidence is in reports/evaluation/PHASE1_RESULTS.md.

### Metric meanings

- **Ground truth:** the known injected or labelled anomaly used to check a detector.
- **Precision:** among confirmed anomalous observations, the fraction that are truly anomalous.
- **Recall:** among truly anomalous observations, the fraction detected.
- **F1 score:** one number balancing precision and recall.
- **Point false-positive rate:** false-positive observations divided by normal observations.
- **False-alert rate:** unmatched confirmed events per 1,000 observations.
- **Detection delay:** observations between ground-truth event start and confirmed detection.
- **Event recall:** fraction of ground-truth event intervals matched by detected intervals.

Detailed definitions and event-matching policy are in reports/evaluation/README.md.

## Public telemetry

ASTRA supports the anonymized SMAP/MSL files referenced by the official Telemanom repository. Data is downloaded only by an explicit command and stored under ignored data/external/telemanom.

Download:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m backend.data.download_telemanom
~~~

Documented sources:

- Repository: https://github.com/khundman/telemanom
- Legacy archive: https://s3-us-west-2.amazonaws.com/telemanom/data.zip
- Dataset currently referenced by the official project: https://www.kaggle.com/datasets/patrickfleith/nasa-anomaly-detection-dataset-smap-msl
- Labels: https://raw.githubusercontent.com/khundman/telemanom/master/labeled_anomalies.csv

Run a small SMAP evaluation:

~~~powershell
.\.venv312\Scripts\python.exe -m backend.evaluation.run --dataset telemanom --mission SMAP --limit-channels 3
~~~

Run a small MSL evaluation:

~~~powershell
.\.venv312\Scripts\python.exe -m backend.evaluation.run --dataset telemanom --mission MSL --limit-channels 3
~~~

Run selected anonymized channels:

~~~powershell
.\.venv312\Scripts\python.exe -m backend.evaluation.run --dataset telemanom --mission SMAP --channels A-1,A-2,A-3
~~~

The loader preserves original train/test arrays, inclusive zero-based anomaly ranges, anonymized channel IDs, and missing timestamps. It does not assign physical units. Telemanom uses a dataset-specific pipeline: rolling statistics for the primary telemetry value plus supplied anonymized command inputs. Its baseline is a median/MAD robust statistical threshold learned from training data, not ASTRA's voltage and temperature limits.

## Test and build

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m pytest backend\tests -q
cd C:\ASTRA\frontend
npm run lint
npm run build
~~~

GitHub Actions repeats backend tests on Windows with Python 3.12 and runs npm clean install, lint and build for the frontend.

## Limitations

- Public Telemanom telemetry is anonymized and pre-scaled. Exact timestamps and physical units are unavailable.
- Simulator performance does not prove generalization to a mission.
- Risk and health scores are prototype heuristics, not failure probabilities.
- Explanations identify evidence patterns and do not confirm root cause.
- ASTRA does not communicate with or control a spacecraft.
- The current API processes batches; the dashboard replay is not a live stream.
- The PyTorch LSTM Autoencoder is an offline Phase 4 experiment. It failed the predeclared integration gate and is not part of the live prototype.

## Phase 1C public-data calibration and holdout

Phase 1C records the six previously viewed channels first, calibrates only on chronological splits of official training arrays plus separately labelled synthetic validation ramps, freezes the selected configuration, and evaluates a deterministic unseen-channel holdout.

Run the phases separately so the freeze boundary is visible:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m backend.evaluation.phase1c diagnose
.\.venv312\Scripts\python.exe -m backend.evaluation.phase1c calibrate
.\.venv312\Scripts\python.exe -m backend.evaluation.phase1c holdout
~~~

For a clean reproduction where no Phase 1C public test result has been viewed, the equivalent single command is:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m backend.evaluation.phase1c all
~~~

The final protocol, all tested validation configurations, selected configuration hash, holdout manifest, per-channel results, aggregate metrics and limitations are under `reports\evaluation`. The public test labels do not participate in parameter selection. An initial holdout execution invalidated during implementation is preserved with a `phase1c_invalidated_initial_` prefix and is excluded from final evidence.

## Phase 2 operator workflow

The simulator API remains backward compatible: `event` contains the primary confirmed event and `events` contains every confirmed episode. Each event has a deterministic identifier, timing, active/resolved status, evidence, detector state and persistence information. `data_quality` is calculated from the returned timestamps and telemetry values.

The live simulation detector is a hybrid rule implemented in `backend\detector.py` and `backend\scoring.py`: fixed operating thresholds plus Isolation Forest only when corroborated by thermal or power trends, followed by three-observation persistence. It is not the frozen Phase 1C public-data configuration. Phase 1C recommends the robust threshold baseline for future operational consideration; Isolation Forest and combined detection remain research comparisons.

Operator acknowledgement, review notes and reviewed status exist only in browser memory for the current session. Event JSON export is generated locally in the browser. No operator history is stored permanently.

Start locally:

~~~powershell
cd C:\ASTRA
.\.venv312\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
~~~

In a second PowerShell window:

~~~powershell
cd C:\ASTRA\frontend
npm run dev -- --host localhost --port 5173
~~~

Open `http://localhost:5173`. FastAPI documentation is at `http://127.0.0.1:8000/docs`.

## Phase 3 release configuration

The frontend reads `VITE_API_BASE_URL` at build time and falls back to `http://127.0.0.1:8000` for local development. The older `VITE_API_URL` name remains a compatibility fallback. Vite variables are public browser configuration, so never place credentials or secrets in them.

For a local non-default API address, copy the example and edit it:

~~~powershell
cd C:\ASTRA\frontend
Copy-Item .env.example .env.local
~~~

For Render, `render.yaml` installs `backend/requirements.txt`, starts Uvicorn on `0.0.0.0:$PORT`, and uses `/api/health`. Set `ALLOWED_ORIGINS` in Render to the comma-separated exact HTTPS frontend origins. Localhost origins and safely formed `*.vercel.app` HTTPS hosts are already accepted by the API CORS policy.

For Vercel, configure the project root as `frontend`, set `VITE_API_BASE_URL` to the HTTPS Render service origin, and deploy with the tracked `frontend/vercel.json`. The production build is `npm run build`, output is `dist`, and the rewrite supports browser-side SPA routing.

Environment variables:

| Variable | Runtime | Required in deployment | Meaning |
|---|---|---|---|
| `ALLOWED_ORIGINS` | Backend | Yes | Comma-separated exact frontend origins allowed by CORS. |
| `VITE_API_BASE_URL` | Frontend build | Yes | Public HTTPS origin of the ASTRA API; contains no secret. |
| `PORT` | Backend | Supplied by Render | Port passed to Uvicorn by `render.yaml`. |

Release instructions and verified boundaries are in `docs/DEMO_RUNBOOK.md`, `docs/TECHNICAL_FACTS.md`, `docs/RELEASE_CHECKLIST.md`, and `docs/WORDING_AUDIT.md`.

## Phase 4 model-selection evidence

The offline research stack evaluated robust thresholding, Isolation Forest, combined detection and a PyTorch LSTM Autoencoder using frozen train, development and holdout protocols on public Telemanom SMAP/MSL telemetry. The LSTM used a 20-observation input window, 12,961 parameters and the shared anonymized `value_0` feature.

On the nine-channel Phase 4 holdout, the LSTM produced fewer false alerts than threshold and combined detection, but event recall fell to 0.307692 and median matched-event delay increased to 121 observations. It failed the predeclared macro-F1 and event-recall checks, so it was not selected for live integration.

Phase 1C and Phase 4 use different frozen holdouts. Compare methods within each experiment only.

Deep learning evaluated, not blindly deployed. ASTRA selects models based on measured mission-safety trade-offs rather than model complexity.

For offline reproduction, create the isolated environment and install the add-on requirements:

~~~powershell
cd C:\ASTRA
py -3.12 -m venv .venv-dl
.\.venv-dl\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv-dl\Scripts\python.exe -m pip install -r backend\requirements-dl.txt
~~~

`backend/requirements-dl.txt` and `.venv-dl` are for offline experimentation only. Render installs only `backend/requirements.txt`; normal FastAPI startup neither requires nor imports PyTorch, and the trained model artifact is not deployed.

See `docs/PPT_CLAIMS.md`, `docs/JUDGE_QA_MODEL_SELECTION.md` and `docs/PHASE5_RELEASE_REPORT.md` for presentation boundaries and the final selection rationale.


## Phase 6 recorded telemetry import

The frontend now offers **Simulated Scenario** and **Recorded CSV Import** sources. Recorded files are limited to CSV, 10 MB and 50,000 rows. They are processed in memory and are not permanently stored.

The only detector-compatible import profile is `astra-sim-v1@1.0`. It requires valid chronological timestamps, continuous sampling, all eight canonical channels, finite complete values, broad sanity bounds and explicit confirmation of the documented units. Valid time-series data that does not meet the complete profile remains visualisation-only: ASTRA suppresses detector events, risk scores and health scores.

Download the template and two ASTRA-generated demonstration files from the import interface. Full format and security details are in `docs/TELEMETRY_IMPORT_FORMAT.md`.

The import endpoint accepts raw CSV bytes at `POST /api/import/telemetry`; `GET /api/import/profile` exposes the supported profile. Event JSON export adds bounded provenance without embedding the uploaded dataset. **Print Report** creates an escaped, print-friendly investigation report that the browser can save as PDF.

ASTRA supports validated import and replay of recorded telemetry that follows its prototype profile; other usable datasets remain visualisation-only. This does not mean ASTRA can analyse arbitrary spacecraft telemetry files.

## Phase 7 release status

The release candidate was verified locally on 2026-09-26: 75 backend tests passed, one optional PyTorch test was skipped, 13 frontend tests passed, lint passed, backend compilation passed, and the production frontend build passed. The approximately 643 kB JavaScript chunk warning remains a documented limitation because a late bundle restructure would add release risk without changing prototype capability.

No deployment was performed during the Phase 7 freeze. Real Render and Vercel URLs are therefore not available and must not be inferred from the example environment files. Follow the deployment order and record the resulting URLs in [docs/PRODUCTION_SMOKE_TEST.md](docs/PRODUCTION_SMOKE_TEST.md).

Release documentation:

- [Final release record](docs/FINAL_RELEASE.md)
- [Production smoke-test record](docs/PRODUCTION_SMOKE_TEST.md)
- [Manual submission checklist](docs/MANUAL_SUBMISSION_CHECKLIST.md)
- [Demonstration runbook](docs/DEMO_RUNBOOK.md)
- [Presentation claims](docs/PPT_CLAIMS.md)
