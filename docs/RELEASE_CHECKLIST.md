# ASTRA release checklist

## Entry and mission-console redesign gate (2026-09-27)

- [x] First-entry screen, session refresh behavior, Launch screen return and focus transfer checked locally
- [x] Backend readiness and Retry checked with Start Replay disabled while unavailable
- [x] Normal, Thermal Fault and Power Fault replay and event evidence checked locally
- [x] Compatible, visualisation-only and invalid CSV paths checked locally
- [x] Detector Comparison Lab and Validation Evidence remain reachable in disclosures
- [x] 320, 680, 980, 1366 and 1920 px entry/console widths show no page-level overflow
- [x] No backend, simulator, detector, score, compatibility or frozen-evidence file changed
- [ ] Persist before/after screenshots to files using a browser or CI runner with screenshot export
- [ ] Verify browser zoom at 200% and an OS-level reduced-motion session
- [ ] Complete browser JSON download and print-dialog inspection in final deployment smoke test

The visual implementation and limitations are documented in `UI_REDESIGN.md` and `UI_VISUAL_QA.md`. This gate does not replace the unchecked production-release items below.

## Automated verification

- [x] Backend tests pass (75 passed, 1 optional PyTorch skip on 2026-09-26)
- [x] Backend compilation passes
- [x] Frontend utility tests pass (13 passed on 2026-09-26)
- [x] Frontend lint passes (2026-09-26)
- [x] Frontend production build passes (2026-09-26)
- [x] `git diff --check` passes

## Local demonstration

- [x] API health endpoint responds
- [x] Normal scenario completes without a persistent event
- [x] Thermal Fault confirms an event
- [x] Power Fault confirms multiple event selection where returned
- [x] Start, pause, resume and reset preserve correct replay state
- [x] Switching scenario clears old events, notes, selection and data quality
- [x] Event selection jumps to the genuine confirmation point
- [x] Acknowledge, review, note and reset remain session-only
- [x] JSON export is valid and labelled `ASTRA prototype event report`
- [x] Validation Evidence expands and remains readable
- [x] Phase 1C and Phase 4 evidence are visibly separated
- [x] Phase 4 LSTM is labelled experimental and not live
- [x] Failed and passed predeclared gates are visible in text
- [x] Backend unavailable and Retry recovery states are clear

## Responsive and accessible review

- [x] 320 px viewport
- [x] 680 px viewport
- [x] 980 px viewport
- [x] 1366 px viewport
- [x] 1920 px viewport
- [x] Keyboard focus is visible and controls have clear names
- [x] Tables scroll inside their containers without page overflow
- [x] Status meaning is present in text, not colour alone
- [x] Reduced-motion preference suppresses the event arrival animation

## Deployment configuration

- [x] Render uses Python 3.12, `$PORT`, `0.0.0.0` and `/api/health`
- [x] Vercel uses `npm run build`, `dist` and an SPA rewrite
- [ ] `VITE_API_BASE_URL` contains the HTTPS backend origin and no secret
- [ ] `ALLOWED_ORIGINS` contains comma-separated exact frontend origins
- [x] Public dataset is not required for API startup
- [x] Render installs only `backend/requirements.txt`
- [x] Production requirements contain no PyTorch
- [x] FastAPI imports while PyTorch is unavailable
- [x] `.venv-dl` and `artifacts/models/` are ignored
- [x] Trained model artifact is not required by frontend or API
- [x] `.venv312`, `node_modules`, build output and real `.env` files are ignored
- [ ] CORS succeeds from the deployed frontend and rejects unrelated origins

## Release administration

- [x] Git status reviewed; Phase 2 checkpoint status recorded
- [x] No detector, telemetry, frozen configuration, holdout or audit artifact changed
- [x] No virtual environment, uploaded telemetry, model artifact, dependency directory, build output, real environment file or temporary report is tracked
- [x] Render and Vercel manifests reviewed against the production contract
- [ ] PPT link verified
- [ ] Video link verified
- [ ] Deployment smoke tests completed

## Phase 7 production gate

- [x] Local API health and documentation return HTTP 200
- [x] Local Normal run returns 180 observations and zero events
- [x] Local Thermal and Power runs return 180 observations and two persistent events each
- [x] Local CORS accepts `http://localhost:5173` and does not allow an unrelated origin
- [x] Existing recorded-import, export, report and frozen-evidence regression tests pass
- [x] Verified local thermal replay displays graph markers, contributing signals, event timeline, detector evidence and operator review
- [ ] Real Render HTTPS URL recorded
- [ ] Real Vercel HTTPS URL recorded
- [ ] Exact production Vercel origin set in Render `ALLOWED_ORIGINS`
- [ ] Production backend health and frontend-to-backend communication verified
- [ ] External-browser JSON download completed and inspected
- [ ] External-browser investigation report saved and inspected as PDF
- [ ] Final production screenshots captured
- [ ] Prototype, video, PPT and QR-code links verified with public-view permissions

Phase 7 is **locally verified but blocked from final release** until every unchecked production and submission item above is completed.

## Phase 8 detector transparency

- [x] Original Normal, Thermal and Power event and score outputs frozen before implementation
- [x] Original fields, event IDs, timing, scores and scenario event counts regression-tested
- [x] Per-observation evidence comes from existing detector and persistence state
- [x] Live pipeline never shows confirmed before hybrid persistence confirms
- [x] Threshold evidence contains genuine measured crossings and configured limits
- [x] Isolation Forest score direction and non-probability boundary are documented
- [x] Comparison Lab is read-only and leaves operator events unchanged
- [x] Synthetic comparison is limited to ASTRA-generated labels
- [x] Compatible unlabelled uploads show no accuracy metrics
- [x] Visualisation-only uploads show no detector conclusions
- [x] LSTM is offline, non-interactive and absent from production imports
- [x] JSON and printable reports add optional escaped detector reasoning without full telemetry
- [x] Frozen Phase 1C and Phase 4 hashes remain under regression protection

## Phase 5 evidence release

- [x] Frozen Phase 1C report and manifest hashes are regression-tested
- [x] Frozen Phase 4 report and manifest hashes are regression-tested
- [x] Frontend evidence values are checked against structured report JSON
- [x] No LSTM scenario or live detector control exists
- [x] Normal simulation release contract remains unchanged
- [x] Export utility regression test remains active
- [x] Presenter claims and model-selection Q&A are documented
- [x] No final holdout was re-run or overwritten

## Bundle record

- Before Phase 3: 613.30 kB JavaScript (182.31 kB gzip); Vite warning present.
- After Phase 3: 614.98 kB JavaScript (182.83 kB gzip); Vite warning remains.
- Decision: retain the single main chunk because Recharts is core dashboard content and splitting it only defers the required telemetry interface.



## Phase 6 recorded import

- [x] CSV extension, 10 MB and 50,000-row limits enforced
- [x] Empty files, duplicate headers and unusable timestamps rejected
- [x] Formula-like cells treated as non-numeric text
- [x] Filenames sanitized and never used as filesystem paths
- [x] Missing, duplicate, out-of-order, gap and constant-channel checks
- [x] One explicit `astra-sim-v1@1.0` detector profile
- [x] Unknown and partial mappings remain visualisation-only
- [x] Visualisation-only replay has no detector, risk or health conclusions
- [x] Source switching clears replay, event selection, reviews and import state
- [x] JSON export includes bounded provenance without full telemetry
- [x] Investigation report contains the exact disclaimer and print stylesheet
- [x] Normal and fault CSVs are labelled ASTRA-generated demonstration data
- [x] Existing simulation and frozen-evidence regression tests remain active
