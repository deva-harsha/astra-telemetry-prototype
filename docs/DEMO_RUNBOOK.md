# ASTRA demo runbook

## Start locally

Use Windows PowerShell. In the first window:

```powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

In a second window:

```powershell
cd C:\ASTRA\frontend
npm ci
npm run dev -- --host localhost --port 5173
```

Open `http://localhost:5173` in a current Chrome, Edge or Firefox release. Confirm the page says **Analysis service ready** before starting.

## Four-minute demonstration

| Time | Action | Point to make |
|---|---|---|
| 0:00–0:25 | State the problem and ASTRA boundary. | Ground teams need persistent anomaly evidence with human review. This is simulated, ground-based decision support with no spacecraft command path. |
| 0:25–1:05 | Choose **Power Fault**, start at 4× speed and show the replay. | Voltage and current behaviour is injected deterministically. Raw values remain in tooltips; the chart alone is normalized for comparison. |
| 1:05–1:40 | Pause and resume, then wait for event confirmation. | The live prototype uses fixed limits, Isolation Forest corroboration, trends and three consecutive candidate observations. |
| 1:40–2:25 | Select each confirmed event and use the graph jump. Inspect contributing signals, timeline and detector evidence. | ASTRA shows what contributed and why review was requested; it does not confirm root cause. |
| 2:25–2:55 | Acknowledge an event, add a short note and export JSON. | Review state is browser-session data; the export is a labelled prototype event report. |
| 2:55–3:25 | Open **Validation evidence** and show Phase 1C. | This is a frozen 20-channel offline public-data baseline evaluation, separate from the simulator. |
| 3:25–3:50 | Show Phase 4, its same-holdout table and failed gate. | The LSTM reduced false alerts but missed more events and detected matched events later. It was evaluated and not selected for live use. |
| 3:50–4:00 | Give the final contribution statement. | ASTRA connects monitoring, persistence, supporting evidence and human review, and selects models using measured trade-offs. |

### Final spoken conclusion

> ASTRA’s contribution is not simply another anomaly-detection model; it connects telemetry monitoring, data-quality checks, persistent-event confirmation, supporting evidence, recorded-data replay and human review in one transparent workflow.

## Scenario details

### Normal Operation

1. Select **Normal Operation**.
2. Start the replay and choose 4× speed.
3. Confirm the run completes with 180 observations and: “No persistent unusual telemetry event was detected in this simulated run.”
4. Confirm the event list remains empty and data-quality counts remain visible.

### Power Fault

1. Reset, select **Power Fault**, and start at 4× speed.
2. Wait for a confirmed event. Select each listed event to jump to its confirmation point.
3. Show the severity text, contributing channels, genuine timestamps, three-observation persistence, and operator message.
4. Add a harmless note, mark reviewed or acknowledged, then export the selected event.

## What to highlight

- Simulated replay, offline public-data evaluation and planned mission integration are separate.
- Risk and health scores are prototype heuristic indicators, not probabilities.
- Fixed limits, Isolation Forest corroboration and persistence contribute to the live simulator decision.
- The Phase 1C public benchmark recommends robust thresholding; that configuration is frozen.
- Phase 4 evaluated a PyTorch LSTM Autoencoder on a different nine-channel frozen holdout. It failed the integration gate and remains offline evidence.
- Phase 1C and Phase 4 values must not be compared directly because their holdout channels differ.
- Every alert requires human review.

## Claims to avoid

Do not claim live spacecraft telemetry, autonomous control, exact failure prediction, confirmed root cause, NASA validation, proven accuracy, operational readiness or a production deep-learning detector.

## Backend fallback

If the service is cold-starting, wait for the connection message and use **Retry**. If it remains unavailable, show the tracked screenshots or validation evidence already loaded in the frontend and explain that the simulator requires the API. Do not invent a result. For a local backup, start the backend with the command above and refresh the page.

## Deployment smoke test

- Open `/api/health` on the Render URL and confirm JSON success.
- Open the Vercel URL in a private window and confirm **Analysis service ready**.
- Run Normal, Thermal Fault and Power Fault once each.
- Check pause/resume/reset, event selection, notes and export.
- Refresh a nested frontend route if one is added; the SPA rewrite must serve `index.html`.
- Confirm browser developer tools show no CORS or mixed-content error.
- Verify `VITE_API_BASE_URL` is the HTTPS Render origin and `ALLOWED_ORIGINS` includes the exact Vercel production origin.


## Phase 6 recorded import demonstration

1. Select **Recorded CSV Import** and confirm previous replay and operator state clear.
2. Download the template, then upload `astra-normal-demo.csv`.
3. Show the sanitized filename, SHA-256 provenance, ten-row preview and quality summary.
4. Confirm the eight canonical mappings and check the unit-confirmation box.
5. Select **Validate mapping** and confirm **Compatible for prototype analysis**.
6. Start, pause, resume and reset the recorded replay.
7. Repeat with `astra-power-fault-demo.csv`, select an event, add a note and acknowledge it.
8. Export JSON and confirm bounded provenance is present and full telemetry is absent.
9. Select **Print Report** and show the exact disclaimer and print layout.
10. Upload a valid timestamp/value CSV with an unknown channel. Confirm visualisation-only replay and no detector, risk or health conclusions.
11. Upload an invalid timestamp CSV and show the specific blocked error.

Say: "ASTRA supports validated import and replay of recorded telemetry that follows its prototype profile; other usable datasets remain visualisation-only."

Do not say: "ASTRA can analyse any spacecraft telemetry file."

## Production handoff

No production URLs were available during the 2026-09-26 release verification. Before a judged demonstration, complete `PRODUCTION_SMOKE_TEST.md`, then run this script once in a private browser against the recorded Vercel URL. Keep the local commands above ready as the fallback; never substitute local results for a failed production check.
