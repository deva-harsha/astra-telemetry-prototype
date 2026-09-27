# ASTRA entry and console redesign

## Scope and starting point

The work began on `main` at `01ab9df` with a clean worktree. It changes the React presentation and documentation. The FastAPI backend, simulator, detector, scores, persistence, API responses, import compatibility, frozen evaluations and report data were left untouched.

The original console placed a large hero above the controls and exposed dense method and validation material on one long page. Several labels and body passages were 9–11 px. CSV mapping stayed expanded after validation, and its ten-row preview and wide provenance grid lengthened the command area. Source inspection and the accessible browser tree both found **one** “What is running” section. The hero was already before import in DOM order; the revised console keeps its compact introduction before the command panel.

## Visual direction

The first browser visit in a session shows a full-viewport ASTRA entry with a navy-black gradient, sparse CSS stars, thin orbital arcs, a faint grid and one slow light accent. All decoration is local CSS and ignores pointer events. No agency marks, raster backgrounds, video, canvas or new animation dependencies are used. The entry copy states the ground-based, prototype and no-command boundaries. Its service line uses the existing `/api/health` readiness state.

The console uses navy-black panels, stronger typography, cyan for active information, green for normal, amber for candidate or warning, coral for critical and violet for research. Colour is paired with text. A sticky header shows the current mission, source, service state and actual browser UTC. The chart and latest values occupy the left side of the desktop workspace; event review occupies the right. The event panel is sticky on wide screens without an internal scroll container. It stacks below telemetry at tablet and mobile widths.

The original normalized chart calculation, raw tooltip values and event markers remain. The new chart panel changes colour and contrast only. The detector pipeline and data-quality summary stay next to the chart. Comparison Lab, “What is running”, Validation Evidence and research boundaries are disclosed below the operational workspace.

## Entry, import and accessibility behavior

- The first entry uses `sessionStorage` only. Refresh after entering opens the console for the current browser session. “Launch screen” returns to the entry without clearing the current app state.
- Entering fades the entry for 440 ms, then moves keyboard focus to the console heading. The reduced-motion preference removes the delay and CSS motion. “Explore Capabilities” opens the method disclosure and focuses its summary. The skip link enters the console if needed.
- Decorative entry elements are hidden from assistive technology. During exit the entry region is hidden and inert. Buttons and disclosure summaries have visible focus outlines.
- Recorded import now exposes the ordered Upload → Map channels → Confirm units → Validate compatibility → Replay and review stepper. A successful explicit validation collapses mapping to a six-field provenance summary; “Edit mapping” restores it. The original file and quality metadata remain under “View validation details.” Validation focuses the telemetry heading. Invalid or failed validation keeps mapping available. Five preview rows appear by default, with an explicit view-all control.
- Original CSV compatibility decisions, unit confirmation, warnings, visualisation-only boundary and backend calls remain as they were.

## Animation and performance boundaries

Only entry opacity and one slow decorative light move. No decoration updates React state, scroll listeners or network requests. `prefers-reduced-motion: reduce` disables the orbit light, entry movement and button lift. The backend health request still starts when `App` mounts, while the entry is visible.

| Production asset | Before | After | Change |
|---|---:|---:|---:|
| JavaScript | 654.41 kB / 192.97 kB gzip | 661.58 kB / 195.11 kB gzip | +7.17 kB / +2.14 kB gzip |
| CSS | 37.67 kB / 7.58 kB gzip | 61.25 kB / 12.23 kB gzip | +23.58 kB / +4.65 kB gzip |

Vite still warns that the single JavaScript chunk exceeds 500 kB. Recharts was already in that chunk. The redesign adds no dependency and no decorative image request. The figures above came from local `npm run build` output.

## Remaining visual limitations

The 320 px console has a tall sticky header and internally scrolling data tables. The operator review column can be taller than the viewport on desktop; it sticks within the workspace and uses normal document scrolling. The single-chunk Recharts warning remains. Browser-based 200% zoom and persistent screenshot files were not available in the local browser tool during this run; viewport checks and captured in-session images are recorded in `UI_VISUAL_QA.md`.
