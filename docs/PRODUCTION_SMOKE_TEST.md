# ASTRA production smoke-test record

## Release under test

| Field | Value |
|---|---|
| Verification date | 2026-09-26 |
| Candidate branch | `release/phase7` |
| Candidate base commit | `ade8c089b3dbab95332b993e89c14b5ef08b61ff` |
| Release commit | Not created; Phase 7 documentation is uncommitted |
| Render HTTPS URL | Not available; deployment was not performed |
| Vercel HTTPS URL | Not available; deployment was not performed |
| Production result | Blocked before deployment step 1: no deployment credentials or project access are available in this workspace |

Do not replace missing URLs with the placeholders in `.env.example` files.

## Required deployment order

1. In Render, create or update the service from the repository `render.yaml` and deploy the release commit.
2. Record the real Render HTTPS origin above and verify `<render-origin>/api/health`.
3. In the Vercel project whose root is `frontend`, set `VITE_API_BASE_URL` to that exact Render HTTPS origin. This is a public origin, not a secret.
4. Deploy the frontend and record the real Vercel HTTPS origin above.
5. Set Render `ALLOWED_ORIGINS` to the exact Vercel production origin, plus any explicitly required preview origins as comma-separated URLs.
6. Redeploy or restart the Render service so the environment update is active.
7. Run every check below from the real Vercel URL in a private browser window.

## Local predeployment evidence

| Check | Result |
|---|---|
| `/api/health` | PASS — HTTP 200 and ASTRA status `ok` |
| FastAPI `/docs` | PASS — HTTP 200 |
| Normal simulation | PASS — 180 observations, 0 events |
| Thermal Fault | PASS — 180 observations, 2 events |
| Power Fault | PASS — 180 observations, 2 events |
| CORS local origin | PASS — `http://localhost:5173` allowed |
| CORS unrelated origin | PASS — no `Access-Control-Allow-Origin` header |
| Browser thermal replay | PASS — 180/180, graph fault/alert markers, two events, contributing signals, timeline, detector evidence and operator review visible |
| Backend tests | PASS — 75 passed, 1 optional PyTorch skip |
| Frontend tests | PASS — 13 passed |
| Lint / build / compileall | PASS |

These are local results. They do not satisfy the production gate.

## Production backend checks

- [ ] `/api/health` returns HTTP 200 and JSON success.
- [ ] `/docs` loads, because documentation is intentionally enabled.
- [ ] Normal returns 180 observations and no event.
- [ ] Thermal Fault returns the expected event fields.
- [ ] Power Fault returns multiple event structures.
- [ ] Compatible CSV size and row limits remain active.
- [ ] Empty, oversized and invalid uploads are rejected safely.
- [ ] A request from the exact Vercel production origin receives the matching CORS allow-origin header.
- [ ] A request from an unrelated origin does not receive an allow-origin header.

## Production frontend checks

- [ ] Initial connection and Render cold-start messages are clear.
- [ ] Start Replay remains disabled until health succeeds.
- [ ] Retry recovers after the backend becomes ready, with no continued health polling afterward.
- [ ] Normal, Thermal and Power runs complete.
- [ ] Compatible demo CSV files download, validate and replay.
- [ ] A usable incompatible CSV remains visualisation-only with no detector, risk or health conclusion.
- [ ] Invalid CSV is blocked with a specific error.
- [ ] Data-quality preview and mapping result appear.
- [ ] Event selection jumps the chart to the genuine confirmation point.
- [ ] Notes, acknowledgement and review state work for the browser session.
- [ ] JSON download completes in an external browser.
- [ ] Print Report opens and saves to PDF.
- [ ] Validation Evidence shows exact Phase 1C and Phase 4 evidence.
- [ ] Browser developer tools show no CORS or mixed-content error.
- [ ] Direct refresh works. No nested application routes currently exist, so a nested-route refresh check is not applicable.
- [ ] The built browser assets contain no secret or local Windows path.

## External export evidence

External Chrome or Edge was not exposed to the release automation environment. The automated frontend tests verify the JSON filename logic, bounded provenance, exclusion of full telemetry, HTML escaping, report content and print CSS. Completion of the browser download dialog and print-to-PDF dialog remains manual; use `MANUAL_SUBMISSION_CHECKLIST.md` and record the downloaded filenames and PDF inspection here.

## Final result

**BLOCKED.** Local release verification passed. Production deployment, live CORS, live frontend-to-backend communication, external-browser export, public links and production screenshots remain unverified.
