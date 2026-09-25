# ASTRA release checklist

## Automated verification

- [x] Backend tests pass
- [x] Frontend utility tests pass
- [x] Frontend lint passes
- [x] Frontend production build passes
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
- [x] `.venv312`, `node_modules`, build output and real `.env` files are ignored
- [ ] CORS succeeds from the deployed frontend and rejects unrelated origins

## Release administration

- [x] Git status reviewed; Phase 2 checkpoint status recorded
- [x] No detector, telemetry, frozen configuration, holdout or audit artifact changed
- [ ] PPT link verified
- [ ] Video link verified
- [ ] Deployment smoke tests completed

## Bundle record

- Before Phase 3: 613.30 kB JavaScript (182.31 kB gzip); Vite warning present.
- After Phase 3: 614.98 kB JavaScript (182.83 kB gzip); Vite warning remains.
- Decision: retain the single main chunk because Recharts is core dashboard content and splitting it only defers the required telemetry interface.

