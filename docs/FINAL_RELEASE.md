# ASTRA Phase 7 final release record

## Product summary

ASTRA is a ground-based spacecraft telemetry decision-support prototype that detects persistent unusual behaviour, connects supporting signal evidence and helps operators investigate confirmed events.

ASTRA’s contribution is not simply another anomaly-detection model; it connects telemetry monitoring, data-quality checks, persistent-event confirmation, supporting evidence, recorded-data replay and human review in one transparent workflow.

## Architecture and capabilities

The Vite and React frontend progressively replays a completed API response and presents telemetry, data quality, confirmed events, evidence and session-only operator review. The FastAPI backend simulates or validates telemetry, applies the live fixed-limit and Isolation Forest workflow, enforces persistence, and returns JSON. Render and Vercel manifests describe the intended production hosting boundary.

Implemented capabilities include deterministic Normal, Thermal Fault and Power Fault simulation; eight physical telemetry channels; fixed limits, Isolation Forest corroboration, trends and three-observation persistence; multiple event review; bounded JSON export; an escaped printable report; recorded CSV mapping and quality checks; compatible replay; visualisation-only fallback; and frozen Phase 1C and Phase 4 evidence.

## Live prototype and offline evaluation boundary

The live prototype uses the simulator-compatible eight-channel profile. The browser replays a completed 180-observation backend batch; it is not a spacecraft stream. Phase 1C and Phase 4 are separate offline research evaluations on anonymized Telemanom SMAP/MSL data with different frozen holdouts. Their values must not be compared across experiments.

## Production status

| Item | Value |
|---|---|
| Render URL | Not available; deployment not performed |
| Vercel URL | Not available; deployment not performed |
| Release commit | Not created; candidate base is `ade8c089b3dbab95332b993e89c14b5ef08b61ff` |
| Release gate | Blocked on deployment and manual submission checks |

The workspace contains no deployment CLI credentials or documented real URLs. Deployment must follow `PRODUCTION_SMOKE_TEST.md`; URLs must be recorded only after the platforms return them.

## Verification totals

- Backend: 75 passed, 1 skipped. The skip is the documented optional PyTorch test.
- Frontend: 13 passed.
- Backend compileall: passed.
- Frontend lint: passed.
- Frontend production build: passed.
- npm clean install: passed with 0 reported vulnerabilities.
- Local API and browser smoke checks: passed as recorded in `PRODUCTION_SMOKE_TEST.md`.

## Deployment configuration

Render uses Python 3.12.8, installs `backend/requirements.txt`, starts Uvicorn on `0.0.0.0:$PORT`, and checks `/api/health`. Production requirements contain no PyTorch. CORS reads exact comma-separated origins from `ALLOWED_ORIGINS`, retains local development origins and accepts safely formed HTTPS `*.vercel.app` origins.

Vercel uses the Vite production build, `dist` output and an SPA rewrite. `VITE_API_BASE_URL` contains the public API origin and must never contain a secret.

## Public evaluation and LSTM decision

ASTRA loaded 81 anonymized Telemanom SMAP/MSL channels for offline evaluation. Phase 1C compares robust thresholding, Isolation Forest and combined detection under its frozen protocol. Phase 4 evaluated a PyTorch LSTM Autoencoder on a separate nine-channel holdout. The LSTM reduced false alerts on that holdout but lowered event recall and increased median matched-event delay. It failed the predeclared integration gate and is not used by the live prototype.

## Recorded-data and security boundaries

ASTRA supports validated import and replay of recorded telemetry that follows its prototype profile; other usable datasets remain visualisation-only.

The supported profile is `astra-sim-v1@1.0`. Import is bounded to CSV, 10 MB, 50,000 rows and 64 columns. Files are processed in memory and are not permanently stored. There is no authentication, database, spacecraft connection or command path. Operator review state is browser-session data. Filenames are sanitized; formula-like CSV cells are not executed; user text is escaped in reports; full uploaded telemetry is excluded from event exports. Vite variables are public browser configuration.

## Known limitations

- Production deployment, URLs, live CORS and public access are unverified.
- External-browser JSON download and print-to-PDF completion are unverified.
- The production build reports one approximately 643 kB JavaScript chunk; no late bundle rewrite was attempted.
- Browser replay is a completed batch, not a live stream.
- The recorded profile assumes its first 60 percent is normal reference telemetry.
- Public telemetry is anonymized and has no mission physical units or timestamps.
- Scores are prototype heuristic indicators, not probabilities.
- Evidence patterns do not confirm root cause or predict failure.

## Presentation evidence plan

No interface images were fabricated. These real states are identified for capture after deployment. The thermal event state was also verified locally on 2026-09-26.

| File to capture | Exact dashboard state |
|---|---|
| `01-main-dashboard.png` | Initial ready screen, Simulated Scenario selected, full workspace visible |
| `02-thermal-confirmed.png` | Completed Thermal Fault replay with a confirmed event and graph markers |
| `03-power-multi-event.png` | Completed Power Fault replay with both genuine events visible |
| `04-event-review.png` | Selected event showing supporting signals, detector evidence, note and acknowledgement |
| `05-csv-compatibility.png` | Compatible CSV mapping, ten-row preview and data-quality summary |
| `06-recorded-replay.png` | Compatible recorded Power replay with provenance context |
| `07-phase1c-evidence.png` | Expanded Phase 1C evidence and method table |
| `08-phase4-gate.png` | Phase 4 failed integration gate and non-live status |
| `09-investigation-report.pdf` | Saved report with disclaimer and reviewed event |

| PPT claim | Screenshot proving it |
|---|---|
| Persistent anomaly detection | `02-thermal-confirmed.png`: confirmed event and graph markers |
| Multi-event workflow | `03-power-multi-event.png`: two genuine Power events |
| Explainable decision support | `04-event-review.png`: supporting signals and detector evidence |
| Recorded data integration | `05-csv-compatibility.png` and `06-recorded-replay.png` |
| Human-in-the-loop review | `04-event-review.png`: acknowledgement, note and review state |
| Evidence-based model selection | `08-phase4-gate.png`: LSTM gate decision |

## Reproduction

```powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m pytest backend\tests -q
.\.venv312\Scripts\python.exe -m compileall backend

cd C:\ASTRA\frontend
npm ci
npm run test
npm run lint
npm run build

cd C:\ASTRA
git diff --check
git status --short
```

Start the local application with the exact commands in the root README. Do not rerun or overwrite frozen Phase 1C or Phase 4 evidence for release verification.
