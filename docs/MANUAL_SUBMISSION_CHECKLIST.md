# ASTRA manual submission checklist

Complete this checklist only against the final deployed release. Record evidence; do not infer success from local tests.

## Deployment and browser smoke test

- [ ] Open the recorded Vercel frontend URL in an incognito or private window.
- [ ] Wait for the Render cold start and confirm **Analysis service ready**.
- [ ] Run Normal Operation and confirm 180 observations with no persistent event.
- [ ] Run Thermal Fault and inspect a genuine confirmed event.
- [ ] Run Power Fault and confirm both genuine events are selectable.
- [ ] Import the compatible Power demo CSV and validate the prototype profile.
- [ ] Import a usable incompatible CSV and confirm it is visualisation-only.
- [ ] Confirm invalid upload blocking and data-quality details.

## External-browser export verification

- [ ] Select a genuine recorded Power event.
- [ ] Add an operator note containing harmless punctuation and angle brackets to check escaping.
- [ ] Acknowledge the event.
- [ ] Download JSON and record the actual filename.
- [ ] Confirm the JSON identifies an `ASTRA prototype event report`.
- [ ] Confirm filename, SHA-256 provenance, event fields, note and acknowledgement match the UI.
- [ ] Confirm the JSON does not contain the full telemetry dataset.
- [ ] Select **Print Report**, save as PDF and record the filename.
- [ ] Inspect every PDF page for page breaks, clipping, exact disclaimer and escaped note text.

## Public submission links

- [ ] Verify the prototype URL from a signed-out browser.
- [ ] Verify the video URL.
- [ ] Verify every PPT link.
- [ ] Verify the QR code resolves to the intended public destination.
- [ ] Confirm **Anyone with the link can view** for every submission artifact.
- [ ] Remove personal information, credentials, local Windows paths and secret values.

## Presentation evidence

- [ ] Capture the main telemetry dashboard.
- [ ] Capture a confirmed Thermal event.
- [ ] Capture the Power timeline with multiple events.
- [ ] Capture selected-event evidence and operator review.
- [ ] Capture CSV compatibility and data-quality preview.
- [ ] Capture recorded telemetry replay.
- [ ] Capture Phase 1C validation evidence.
- [ ] Capture the Phase 4 LSTM gate decision.
- [ ] Keep the inspected investigation-report PDF.
- [ ] Use only actual production or verified local interface states; do not fabricate or alter results.

## Final backup and freeze

- [ ] Keep a local demo backup with the verified Python environment and npm lockfile.
- [ ] Record the final Render URL, Vercel URL, release commit and tag in `PRODUCTION_SMOKE_TEST.md` and `FINAL_RELEASE.md`.
- [ ] Re-run the release gate after any post-verification change.
- [ ] Confirm no uncommitted or untracked release files remain.
