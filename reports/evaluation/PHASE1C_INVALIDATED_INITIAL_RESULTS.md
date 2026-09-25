# ASTRA Phase 1C results

This is offline research evidence on anonymized, pre-scaled public telemetry. It does not establish operational readiness.

## Frozen protocol

- Configuration hash: `bbb4157d27ba929526c48b040cd6524c6df26f54378dc48011f4835d678533d6`
- Features: `combined`; window 10; persistence 5
- Robust threshold: 4.0 train-fitted robust scale units
- Isolation Forest: contamination 0.02, estimators 100, validation score quantile 0.01
- Combined rule: `or`
- Preprocessing and Isolation Forest fit only the first chronological part of each official training array. The later training portion calibrates normal false alerts and the model score cutoff. Official test arrays remain untouched until final evaluation.
- Synthetic validation ramps are labelled synthetic and are used only to compare sensitivity. They are not NASA anomalies.

## Holdout channels

- SMAP: G-3, G-7, A-9, E-1, F-3, A-8, E-9, E-6, D-4, E-2
- MSL: P-10, D-15, T-4, M-5, S-2, M-6, M-7, M-2, T-8, F-5

## Micro results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay | Time ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| threshold | 0.677753 | 0.259205 | 0.374994 | 0.021695 | 0.250000 | 0.355282 | 24.0 | 32.920 |
| isolation_forest | 0.112304 | 0.088491 | 0.098986 | 0.123129 | 0.333333 | 2.496083 | 68.25 | 5401.399 |
| combined | 0.265755 | 0.279228 | 0.272325 | 0.135803 | 0.375000 | 1.084065 | 36.222222 | 5460.048 |

## Macro results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay |
|---|---:|---:|---:|---:|---:|---:|---:|
| threshold | 0.192742 | 0.210815 | 0.176568 | 0.026010 | 0.300000 | 0.793152 | 24.0 |
| isolation_forest | 0.247706 | 0.159538 | 0.058447 | 0.106793 | 0.300000 | 1.843858 | 81.0 |
| combined | 0.238737 | 0.297781 | 0.164854 | 0.125724 | 0.350000 | 1.289082 | 38.0 |

## Per-channel results

| Mission | Channel | Method | F1 | Event recall | Point FPR | False alerts / 1,000 | Mean delay | Best |
|---|---|---|---:|---:|---:|---:|---:|---|
| SMAP | G-3 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | G-3 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | G-3 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | G-7 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| SMAP | G-7 | isolation_forest | 0.151724 | 1.000000 | 0.000000 | 0.747291 | 30.0 | isolation_forest |
| SMAP | G-7 | combined | 0.151724 | 1.000000 | 0.000000 | 0.747291 | 30.0 | isolation_forest |
| SMAP | A-9 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | A-9 | isolation_forest | 0.000000 | 0.000000 | 0.098052 | 1.067109 | — | threshold |
| SMAP | A-9 | combined | 0.000000 | 0.000000 | 0.098052 | 1.067109 | — | threshold |
| SMAP | E-1 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-1 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-1 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | F-3 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| SMAP | F-3 | isolation_forest | 0.009747 | 0.000000 | 0.999520 | 0.119389 | — | isolation_forest |
| SMAP | F-3 | combined | 0.009747 | 0.000000 | 0.999520 | 0.119389 | — | isolation_forest |
| SMAP | A-8 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| SMAP | A-8 | isolation_forest | 0.099606 | 1.000000 | 0.010506 | 7.402985 | 110.0 | isolation_forest |
| SMAP | A-8 | combined | 0.099606 | 1.000000 | 0.010506 | 7.402985 | 110.0 | isolation_forest |
| SMAP | E-9 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-9 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-9 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-6 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-6 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-6 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-4 | threshold | 0.999076 | 1.000000 | 0.000000 | 0.000000 | 6.0 | threshold |
| SMAP | D-4 | isolation_forest | 0.460956 | 1.000000 | 0.000766 | 18.529446 | 14.0 | threshold |
| SMAP | D-4 | combined | 0.998460 | 1.000000 | 0.000766 | 0.118022 | 6.0 | threshold |
| SMAP | E-2 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-2 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-2 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | P-10 | threshold | 0.124224 | 1.000000 | 0.231027 | 0.000000 | 31.0 | isolation_forest |
| MSL | P-10 | isolation_forest | 0.162571 | 1.000000 | 0.140895 | 4.754098 | 31.0 | isolation_forest |
| MSL | P-10 | combined | 0.124224 | 1.000000 | 0.231027 | 0.000000 | 31.0 | isolation_forest |
| MSL | D-15 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | D-15 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | D-15 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-4 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-4 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-4 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-5 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-5 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-5 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | S-2 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | S-2 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | S-2 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-6 | threshold | 0.912568 | 1.000000 | 0.009636 | 0.000000 | 14.0 | threshold |
| MSL | M-6 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-6 | combined | 0.912568 | 1.000000 | 0.009636 | 0.000000 | 14.0 | threshold |
| MSL | M-7 | threshold | 0.617450 | 1.000000 | 0.000973 | 0.463822 | 18.0 | threshold |
| MSL | M-7 | isolation_forest | 0.099852 | 0.000000 | 0.886131 | 0.927644 | — | threshold |
| MSL | M-7 | combined | 0.099852 | 0.000000 | 0.886131 | 0.927644 | — | threshold |
| MSL | M-2 | threshold | 0.640657 | 1.000000 | 0.161092 | 13.614405 | 44.0 | threshold |
| MSL | M-2 | isolation_forest | 0.025952 | 1.000000 | 0.000000 | 3.074220 | 269.0 | threshold |
| MSL | M-2 | combined | 0.640657 | 1.000000 | 0.161092 | 13.614405 | 44.0 | threshold |
| MSL | T-8 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-8 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-8 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | F-5 | threshold | 0.237389 | 1.000000 | 0.117475 | 1.784804 | 31.0 | combined |
| MSL | F-5 | isolation_forest | 0.158537 | 1.000000 | 0.000000 | 0.254972 | 32.0 | combined |
| MSL | F-5 | combined | 0.260234 | 1.000000 | 0.117741 | 1.784804 | 31.0 | combined |

## Decision

Recommended public-data method: **threshold**.

Combined did not clear the predeclared bar of higher point F1, no lower event recall, and no higher false-alert rate; the stronger simpler baseline is preferred.

Channel wins: {'threshold': 15, 'isolation_forest': 4, 'combined': 1}.

An LSTM experiment is not justified by this phase alone. A sequence model would add complexity before the simpler baselines show stable cross-channel calibration, and the current anonymized channel-by-channel protocol lacks a defensible sequence-training target.

## Limitations

- Telemanom channels are anonymized and pre-scaled upstream; physical units and exact mission timing are unavailable.
- Public training arrays are treated as normal because they contain no official interval labels; undetected contamination may exist.
- Synthetic validation ramps test sensitivity to one artificial pattern and cannot represent all spacecraft anomalies.
- One frozen 20-channel holdout is evidence for this protocol only. It is not an operational qualification.
- Timing is machine-dependent and includes per-channel model fitting for Isolation Forest and combined methods.
