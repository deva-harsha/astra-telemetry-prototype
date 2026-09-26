# ASTRA Phase 8 report

## Result

Phase 8 makes the existing detector path visible without changing its validated decisions. The API now appends structured `detector_reasoning` to compatible observations and events. The frontend shows a live pipeline, selected-event reasoning, a read-only detector comparison, synthetic label timing where available, and the offline LSTM decision.

## Preserved behavior

Before implementation, deterministic snapshots were saved for Normal, Thermal Fault and Power Fault. They cover metadata, every original score and severity field, event IDs, event timing, event fields and metrics other than nondeterministic processing latency. Regression tests compare the current response against those snapshots while ignoring only new additive evidence fields.

The original candidate expressions, three-observation persistence mask, risk and health formulas, event episode grouping, event ID format and primary-event selection are unchanged. Frozen Phase 1C and Phase 4 evidence is guarded by the existing hash tests.

## Architecture

- `backend/reasoning.py` converts existing detector and scoring columns into JSON-safe evidence.
- Per-observation evidence is appended to both simulated and compatible recorded responses.
- Event reasoning is captured from the genuine alert-confirmation observation.
- Visualisation-only responses contain no reasoning, metrics or events.
- The Comparison Lab derives method summaries in the browser from returned evidence and never calls or mutates the operational workflow.
- No comparison endpoint was added because the existing response safely supports a read-only comparison.

## Comparison boundary

Threshold-only and Isolation-Forest-only confirmed episodes use persistence masks already calculated by the existing scorer. The hybrid remains the only source of operator events. Method processing times are omitted because the current run does not measure them separately. Isolation Forest channel attribution is shown as unavailable rather than inferred.

## Export boundary

JSON event exports optionally include `detector_reasoning`. Printable reports add escaped threshold, model, trend, persistence and final-logic fields. They retain bounded provenance, exclude complete telemetry, omit LSTM outputs and do not present Comparison Lab output as an operational conclusion.

## Verification

- Backend: 80 passed, 1 documented optional PyTorch skip.
- Frontend: 16 passed; lint and production build passed.
- Backend compilation passed.
- Browser checks covered the empty state, Normal pre-event states, Thermal reasoning, Power with two events, threshold/model disagreement, hybrid confirmation, comparison summaries, synthetic boundary, compatible CSV validation and visualisation-only suppression.
- CSS contains dedicated single-column layouts for the new pipeline and comparison cards below 680 px. Existing responsive behavior remains covered by the unchanged layout rules; automated browser viewport resizing was unavailable in the in-app browser.
- Backend unavailable and retry behavior remains unchanged and was previously release-verified; Phase 8 does not modify that code.

No commit, push, merge, tag or deployment was performed.
