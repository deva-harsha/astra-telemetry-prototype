# ASTRA visual QA record

## Baseline

Inspected `main` at `01ab9df` before editing and again from a temporary, unmodified Git HEAD preview. The accessible browser tree showed one “What is running” heading and a large console hero before source selection. The old page used multiple 9–11 px labels, always-visible mapping and ten preview rows. Baseline production assets were 654.41 kB JavaScript (192.97 kB gzip) and 37.67 kB CSS (7.58 kB gzip). Baseline screenshots were captured in the browser session at all five required widths. At 1366 px, the old chart began about 1181 px below the viewport top; the redesigned chart began about 984 px below the top in the same 900 px viewport. The screenshot API returned image bytes for inspection but did not provide a supported local save path.

## Responsive checks

The browser viewport override was set to each width at a 900 px height. Screenshots were captured in the browser session for the baseline console and redesigned entry and console at each width. The browser measured `document.documentElement.scrollWidth` against `innerWidth`. Tables were allowed to scroll internally. The temporary original-layout preview was removed after capture.

| Width | Entry page overflow | Console page overflow | Workspace |
|---:|:---:|:---:|---|
| 320 px | No | No | Stacked; telemetry table scrolls internally |
| 680 px | No | No | Stacked |
| 980 px | No | No | Stacked |
| 1366 px | No | No | Approximately 2.15:1; event review sticky |
| 1920 px | No | No | Approximately 2.15:1; event review sticky |

The entry action measured 52 px high at all five widths. Its heading ranged from 43.2 px at 320 to 120 px at 1920. The light, grid, stars and arcs are CSS only. Decorative layers use `pointer-events: none`.

## Interaction checks

| Check | Result |
|---|---|
| First visit, Enter Mission Control, heading focus | Passed in browser |
| Launch-screen return and session refresh | Passed in browser; refresh opened the console |
| Explore Capabilities | Passed; disclosure opened and summary received focus |
| Backend cold-start and Retry | Passed; Start stayed disabled until service ready |
| Normal simulated replay | Passed; 180 observations, zero persistent events |
| Thermal Fault | Passed; confirmed thermal events visible |
| Power Fault | Passed; power event and genuine contributing rows visible |
| Compatible recorded CSV | Passed; mapping, unit confirmation, validation, replay, collapsed summary and focus transfer |
| Visualisation-only CSV | Passed; detector and score boundary visible |
| Invalid CSV | Passed; timestamp error shown and replay blocked |
| Detector Comparison Lab and Validation Evidence | Passed; both disclosures opened |
| Reduced motion | Utility and CSS checks passed; an OS-level reduced-motion browser session was not available |
| 200% browser zoom | Not performed; 320/680 px viewports covered narrow layouts but are not a substitute for zoom |
| JSON download and browser print dialog | Report builders passed existing automated tests; final browser download/print interaction remains to be checked |

## Screenshots

Before and after images were inspected through the in-app browser screenshot tool. The tool did not expose a supported way to persist its screenshot bytes as files. A separate local headless browser process failed during GPU initialization, and browser policy blocked a data-URL save path. **There are no local screenshot file locations to claim.** Before release, capture named PNGs for the entry and console at the five widths through a browser or CI runner that supports saving screenshots, then link them here.

## Regression gate

`backend/tests` passed with 80 passed and one optional skip. Frontend tests passed with 22 passed after the presentation tests were added. Final lint, build, compileall and diff checks are recorded at completion. No backend files or frozen evaluation files were changed.
