# ASTRA Phase 1C results

This is offline research evidence on anonymized, pre-scaled public telemetry. It does not establish operational readiness.

## Frozen protocol

- Configuration hash: `1749b3b56198cf9d3f016a2c690354e2f48cf5d39b4e8810fa59fbfb2e7f46e2`
- Features: `rolling`; window 10; persistence 5
- Robust threshold: 4.0 train-fitted robust scale units
- Isolation Forest: contamination 0.02, estimators 100, validation score quantile 0.01
- Combined rule: `or`
- Preprocessing and Isolation Forest fit only the first chronological part of each official training array. The later training portion calibrates normal false alerts and the model score cutoff. Official test arrays remain untouched until final evaluation.
- Synthetic validation ramps are labelled synthetic and are used only to compare sensitivity. They are not NASA anomalies.

## Holdout channels

- SMAP: D-5, D-2, E-11, F-1, D-1, D-3, D-13, P-1, P-3, D-9
- MSL: T-9, P-15, F-4, P-11, P-14, T-5, M-1, T-13, M-3, T-12

## Protocol audit

An initial holdout execution was invalidated because parameter variants had not been tested with the feature set favored by the ablation. Its artifacts are preserved with the `phase1c_invalidated_initial_` prefix and none of its channels appear in the final holdout. The correction was driven by validation-protocol structure, not by holdout performance.

## Validation-only feature ablation

| Feature set | Normal validation FPR | Synthetic validation F1 | Synthetic event recall | Selection score |
|---|---:|---:|---:|---:|
| raw | 0.000000 | 0.599530 | 1.000000 | 0.579714 |
| rolling | 0.000672 | 0.645186 | 1.000000 | 0.624380 |
| difference | 0.000000 | 0.481088 | 1.000000 | 0.477563 |
| combined | 0.000224 | 0.495791 | 1.000000 | 0.491173 |

Rolling features won the controlled ablation. First difference was removed. The missing-value indicator is retained so missingness first appearing after fitting remains observable; train-constant telemetry-derived features are removed per channel.

## Development channels before and after calibration

Phase 1B combined results were SMAP F1 0.018843 / point FPR 0.350946 / event recall 0.000000, and MSL F1 0.256133 / point FPR 0.227468 / event recall 0.833333. Those mission aggregates are retained in the Phase 1B report.

Across all six channels after the frozen Phase 1C calibration, combined F1 was 0.147493, point FPR 0.006624, event recall 0.333333, and false alerts/1,000 0.536295.

The false-positive rate improved sharply, but event recall fell. This is calibration trade-off evidence, not a claim that every metric improved.

## Micro results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay | Time ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| threshold | 0.284087 | 0.388582 | 0.328218 | 0.177143 | 0.461538 | 1.693267 | 134.333333 | 24.481 |
| isolation_forest | 0.297176 | 0.175094 | 0.220356 | 0.074910 | 0.384615 | 3.647729 | 62.9 | 4192.510 |
| combined | 0.295063 | 0.422037 | 0.347309 | 0.182397 | 0.500000 | 2.413806 | 67.692308 | 4235.414 |

## Macro results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts / 1,000 | Mean delay |
|---|---:|---:|---:|---:|---:|---:|---:|
| threshold | 0.207157 | 0.266144 | 0.139126 | 0.166085 | 0.483333 | 2.143601 | 136.0 |
| isolation_forest | 0.209426 | 0.167489 | 0.111960 | 0.062371 | 0.416667 | 3.002554 | 68.388889 |
| combined | 0.217872 | 0.322969 | 0.179961 | 0.173584 | 0.533333 | 2.961759 | 57.454545 |

## Mission macro comparison

| Mission | Method | F1 | Event recall | Point FPR | False alerts / 1,000 |
|---|---|---:|---:|---:|---:|
| SMAP | threshold | 0.195699 | 0.566667 | 0.107374 | 1.437546 |
| SMAP | isolation_forest | 0.143321 | 0.433333 | 0.008792 | 4.275041 |
| SMAP | combined | 0.248629 | 0.466667 | 0.108154 | 1.978397 |
| MSL | threshold | 0.082553 | 0.400000 | 0.224795 | 2.849655 |
| MSL | isolation_forest | 0.080598 | 0.400000 | 0.115950 | 1.730066 |
| MSL | combined | 0.111294 | 0.600000 | 0.239015 | 3.945121 |

## Detection-delay distribution

| Method | Matches | Minimum | Median | P90 | Maximum |
|---|---:|---:|---:|---:|---:|
| threshold | 12 | 4 | 47.0 | 354.9 | 518 |
| isolation_forest | 10 | 6 | 26.0 | 109.3 | 301 |
| combined | 13 | 4 | 32.0 | 152.8 | 300 |

## Per-channel results

| Mission | Channel | Method | F1 | Event recall | Point FPR | False alerts / 1,000 | Mean delay | Best |
|---|---|---|---:|---:|---:|---:|---:|---|
| SMAP | D-5 | threshold | 0.011217 | 1.000000 | 0.999472 | 0.131096 | 22.0 | isolation_forest |
| SMAP | D-5 | isolation_forest | 0.042934 | 1.000000 | 0.065461 | 14.682748 | 15.0 | isolation_forest |
| SMAP | D-5 | combined | 0.013290 | 0.000000 | 0.999472 | 0.131096 | — | isolation_forest |
| SMAP | D-2 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-2 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-2 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-11 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-11 | isolation_forest | 0.000000 | 0.000000 | 0.000365 | 0.352361 | — | threshold |
| SMAP | E-11 | combined | 0.000000 | 0.000000 | 0.000365 | 0.352361 | — | threshold |
| SMAP | F-1 | threshold | 0.021413 | 1.000000 | 0.042556 | 10.834110 | 32.0 | combined |
| SMAP | F-1 | isolation_forest | 0.000000 | 0.000000 | 0.001532 | 0.232992 | — | combined |
| SMAP | F-1 | combined | 0.024440 | 1.000000 | 0.045267 | 10.601118 | 32.0 | combined |
| SMAP | D-1 | threshold | 0.941368 | 1.000000 | 0.000000 | 0.000000 | 361.0 | threshold |
| SMAP | D-1 | isolation_forest | 0.108639 | 1.000000 | 0.002667 | 4.935950 | 59.0 | threshold |
| SMAP | D-1 | combined | 0.940434 | 1.000000 | 0.002667 | 0.705136 | 59.0 | threshold |
| SMAP | D-3 | threshold | 0.964053 | 1.000000 | 0.025913 | 0.000000 | 98.0 | combined |
| SMAP | D-3 | isolation_forest | 0.743743 | 1.000000 | 0.016219 | 17.013889 | 79.0 | combined |
| SMAP | D-3 | combined | 0.964642 | 1.000000 | 0.027964 | 0.462963 | 79.0 | combined |
| SMAP | D-13 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-13 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-13 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | P-1 | threshold | 0.010000 | 0.666667 | 0.005803 | 3.057025 | 234.5 | threshold |
| SMAP | P-1 | isolation_forest | 0.005222 | 0.333333 | 0.001677 | 1.058201 | 301.0 | threshold |
| SMAP | P-1 | combined | 0.010000 | 0.666667 | 0.005803 | 3.057025 | 234.5 | threshold |
| SMAP | P-3 | threshold | 0.008942 | 1.000000 | 0.000000 | 0.353232 | 518.0 | combined |
| SMAP | P-3 | isolation_forest | 0.532674 | 1.000000 | 0.000000 | 4.474273 | 18.0 | combined |
| SMAP | P-3 | combined | 0.533480 | 1.000000 | 0.000000 | 4.474273 | 18.0 | combined |
| SMAP | D-9 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-9 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-9 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-9 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-9 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-9 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | P-15 | threshold | 0.013550 | 1.000000 | 0.509700 | 0.000000 | 11.0 | isolation_forest |
| MSL | P-15 | isolation_forest | 0.068966 | 1.000000 | 0.041975 | 6.652661 | 11.0 | isolation_forest |
| MSL | P-15 | combined | 0.012870 | 1.000000 | 0.537213 | 3.501401 | 11.0 | isolation_forest |
| MSL | F-4 | threshold | 0.000000 | 0.000000 | 0.005968 | 0.584454 | — | isolation_forest |
| MSL | F-4 | isolation_forest | 0.152809 | 1.000000 | 0.101462 | 5.260082 | 31.0 | isolation_forest |
| MSL | F-4 | combined | 0.152809 | 1.000000 | 0.101462 | 5.260082 | 31.0 | isolation_forest |
| MSL | P-11 | threshold | 0.403909 | 1.000000 | 0.005141 | 1.414427 | 17.5 | combined |
| MSL | P-11 | isolation_forest | 0.470588 | 1.000000 | 0.005745 | 1.697313 | 13.5 | combined |
| MSL | P-11 | combined | 0.486804 | 1.000000 | 0.009072 | 2.545969 | 13.5 | combined |
| MSL | P-14 | threshold | 0.057671 | 0.000000 | 0.999324 | 0.163934 | — | threshold |
| MSL | P-14 | isolation_forest | 0.057671 | 0.000000 | 0.999324 | 0.163934 | — | threshold |
| MSL | P-14 | combined | 0.057671 | 0.000000 | 0.999324 | 0.163934 | — | threshold |
| MSL | T-5 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-5 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-5 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-1 | threshold | 0.030464 | 1.000000 | 0.304577 | 6.587615 | 4.0 | threshold |
| MSL | M-1 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-1 | combined | 0.030464 | 1.000000 | 0.304577 | 6.587615 | 4.0 | threshold |
| MSL | T-13 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-13 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | T-13 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-3 | threshold | 0.319936 | 1.000000 | 0.423241 | 19.746121 | 62.0 | threshold |
| MSL | M-3 | isolation_forest | 0.000000 | 0.000000 | 0.003198 | 1.880583 | — | threshold |
| MSL | M-3 | combined | 0.316375 | 1.000000 | 0.430704 | 19.746121 | 62.0 | threshold |
| MSL | T-12 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| MSL | T-12 | isolation_forest | 0.055944 | 1.000000 | 0.007796 | 1.646091 | 88.0 | isolation_forest |
| MSL | T-12 | combined | 0.055944 | 1.000000 | 0.007796 | 1.646091 | 88.0 | isolation_forest |

## Decision

Recommended public-data method: **threshold**.

Combined did not clear the predeclared bar of higher point F1, no lower event recall, and no higher false-alert rate; the stronger simpler baseline is preferred.

Channel wins: {'threshold': 12, 'isolation_forest': 4, 'combined': 4}.

An LSTM experiment is not justified by this phase alone. A sequence model would add complexity before the simpler baselines show stable cross-channel calibration, and the current anonymized channel-by-channel protocol lacks a defensible sequence-training target.

## Limitations

- Telemanom channels are anonymized and pre-scaled upstream; physical units and exact mission timing are unavailable.
- Public training arrays are treated as normal because they contain no official interval labels; undetected contamination may exist.
- Synthetic validation ramps test sensitivity to one artificial pattern and cannot represent all spacecraft anomalies.
- One frozen 20-channel holdout is evidence for this protocol only. It is not an operational qualification.
- Timing is machine-dependent and includes per-channel model fitting for Isolation Forest and combined methods.
