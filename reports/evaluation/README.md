# ASTRA evaluation reports

latest.json and latest.csv are generated only after a successful evaluation run and are ignored by Git until reviewed.

## Metric definitions

- **Point precision:** confirmed anomalous observations that overlap ground truth divided by all confirmed anomalous observations.
- **Point recall:** ground-truth anomalous observations detected after persistence divided by all ground-truth anomalous observations.
- **Point F1:** harmonic mean of point precision and recall.
- **Event recall:** ground-truth intervals matched by a detected interval divided by all ground-truth intervals.
- **False positive observations:** confirmed observations outside ground truth.
- **Point false-positive rate:** false-positive observations divided by all normal observations.
- **False confirmed events:** contiguous confirmed intervals that match no ground-truth event.
- **False alerts per 1,000 observations:** unmatched confirmed intervals divided by evaluated observations, multiplied by 1,000.
- **Missed events:** ground-truth intervals with no match.
- **Detection delay:** detected interval start minus ground-truth interval start, in observation indices.
- **Processing time:** measured wall-clock time for the documented evaluation scope; it is not spacecraft transmission latency.

A detected interval matches when its start lies within the ground-truth interval or within the configured event_matching_tolerance around that interval. An alert that began earlier than the tolerance is treated as a pre-existing false alert even if it remains active into a later labelled event.

Each generated JSON report records the data source, configuration, split policy, UTC run date, Git commit and metrics. Synthetic results use independent seeds for normal training, validation and held-out testing. Telemanom results preserve its supplied train/test files.

## Known limitations

Simulator results do not prove mission generalization. Telemanom channels and times are anonymized, values are pre-scaled, and MSL does not provide a uniform timestamp cadence. The three methods share data loading and feature-generation overhead, so processing time is scoped explicitly rather than presented as pure model inference latency.



## Phase 1C artifacts

- `phase1c_development_channels.csv` and `.md`: six-channel diagnosis recorded before calibration.
- `phase1c_calibration.csv`: every feature-ablation and parameter configuration with normal-validation and synthetic-validation metrics.
- `phase1c_selected_config.json`: immutable selected configuration plus its canonical SHA-256.
- `phase1c_development_after_calibration.csv` and `.json`: diagnostic comparison generated only after the config was frozen.
- `phase1c_holdout_manifest.json`: deterministic final channel selection and exclusions, written before performance calculation.
- `phase1c_holdout_results.csv` and `.json`: final per-channel and aggregate evidence.
- `PHASE1C_RESULTS.md`: human-readable protocol, results, decision and limitations.
- Files prefixed `phase1c_invalidated_initial_` preserve an implementation audit trail. They are not final holdout evidence.

Phase 1C fits preprocessing and Isolation Forest only on the first chronological section of each official training array. Its later training section controls normal false-alert behavior and the Isolation Forest score cutoff. Official test arrays and labels are used only after configuration freeze. Synthetic validation ramps are not NASA anomalies.
