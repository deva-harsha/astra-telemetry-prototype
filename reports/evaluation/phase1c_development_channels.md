# Phase 1C development-channel diagnosis

These six official test channels were already viewed in Phase 1B. They are diagnostic data, not holdout evidence. No Phase 1C parameter was selected from their labels or test metrics.

| Mission | Channel | Train / test | Events | Anomaly % | Mean shift (train SD) | Outside train range % | Constant features | Threshold F1 | IF F1 | Combined F1 | Best |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SMAP | A-1 | 2880 / 8640 | 1 | 0.984 | 768518.519 | 100.000 | 7 | 0.0195 | 0.0000 | 0.0195 | threshold |
| SMAP | A-2 | 2648 / 7914 | 1 | 1.403 | 0.154 | 0.000 | 7 | 0.0000 | 0.0000 | 0.0000 | threshold |
| SMAP | A-3 | 2736 / 8205 | 1 | 2.267 | 0.089 | 0.000 | 7 | 0.0000 | 0.0000 | 0.0000 | threshold |
| MSL | C-1 | 2158 / 2264 | 2 | 13.781 | 0.170 | 0.000 | 40 | 0.0000 | 0.0485 | 0.0469 | isolation_forest |
| MSL | C-2 | 764 / 2051 | 2 | 6.680 | 472131419.262 | 77.182 | 47 | 0.1422 | 0.0000 | 0.1422 | threshold |
| MSL | D-14 | 3675 / 2625 | 2 | 8.457 | 140517006.803 | 7.086 | 36 | 0.9010 | 0.0090 | 0.9010 | threshold |

## Findings recorded before calibration

- Several channels have strong train-to-test level or range shift. A fixed train-median robust threshold therefore creates long alerts before labelled events.
- The legacy Isolation Forest cutoff is too conservative on some channels and its unscaled mixed features are dominated by channel-specific ranges and command indicators.
- Every channel contains near-constant command features. They add dimensions without useful variance and can distort distance-based splits.
- The legacy test feature calculation starts rolling windows with no training history, creating avoidable boundary differences.
- Persistence suppresses isolated points but cannot repair a threshold that remains active through a shifted normal regime.
- Isolation Forest score direction is reported per channel; `decision_function` is lower for more unusual samples. Direction checks that fail show score ordering does not align with labels, not a reversed comparator.
- Event matching rejects alerts that began more than two observations before a labelled interval, so long pre-existing alerts cannot claim later events. Tolerated early starts are recorded as zero delay.
- The public archive is already pre-scaled by its publisher. Phase 1C still applies train-only per-channel robust scaling; the source archive's upstream scaling cannot be undone.
