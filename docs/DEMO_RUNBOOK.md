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
| 0:00–0:30 | State the boundary and show the three-step guide. | Simulated telemetry demonstration; ground-based decision support; human review required; no spacecraft command access. |
| 0:30–1:15 | Choose **Normal Operation**, start at 4× speed, and move through subsystem tabs. | The control run has no injected fault. Values remain available in physical units; the chart scales signals only for comparison. |
| 1:15–1:40 | Pause, resume, and show Run Analysis Time and data quality. | Playback controls affect the browser replay. Analysis time is genuine backend execution time. |
| 1:40–2:55 | Reset, choose **Power Fault**, start at 4× speed, and wait for confirmation. | The simulated voltage/current pattern must persist for three candidate observations before an event is confirmed. |
| 2:55–3:35 | Select an event, jump to it, inspect contributing signals, timeline and detector evidence. | The evidence supports review; it does not confirm a root cause. |
| 3:35–4:00 | Add a session note, acknowledge, export JSON, and open Validation evidence. | Review state is browser-session data. The public benchmark is offline initial research evidence, not operational validation. |

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
- Every alert requires human review.

## Claims to avoid

Do not claim live spacecraft telemetry, autonomous control, exact failure prediction, confirmed root cause, NASA validation, proven accuracy, operational readiness or a deployed deep-learning model.

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
