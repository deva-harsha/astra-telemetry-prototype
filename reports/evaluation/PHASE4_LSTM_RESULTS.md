# ASTRA Phase 4 LSTM autoencoder results

Offline research on anonymized, pre-scaled public telemetry. This is not operational validation and is not integrated into the simulator, API, dashboard, or deployment.

## Framework and hardware

- Python 3.12.14; PyTorch 2.14.0+cpu; NumPy 2.5.3
- Device: CPU; MKL-DNN: True; CUDA: False
- Processor: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel; logical CPUs: 12
- PyTorch provides an official Windows CPU wheel for Python 3.12 and remains isolated from ASTRA production.

## Dataset and separation

Telemanom SMAP/MSL arrays are anonymized and pre-scaled. Each official training array was split chronologically: first 70% for scaler/model fitting and final 30% for normal validation and threshold selection. Official test labels were not used for model or threshold selection.

Development channels: SMAP A-1, A-2, A-3; MSL C-1, C-2, D-14. Synthetic validation ramps are artificial sensitivity checks, not NASA anomalies.

Final holdout:
- MSL: F-7, D-16, F-8, M-4
- SMAP: P-7, D-7, G-1, E-13, B-1

## Development selection

- Selected configuration: lstm-03
- Normal-validation point FPR: 0.002913; false alerts/1,000: 0.896459
- Separately labelled synthetic-ramp F1: 0.951627; event recall: 1.000000
- Synthetic validation results are sensitivity checks, not NASA anomaly performance.

## Window construction and model

- Window 20; training stride 4; inference stride 1
- Windows never cross channel boundaries. Each score belongs to its window end; the first window_size - 1 observations remain unscored.
- Features: value_0; pooled-channel train-fit median/MAD scaling; globally train-constant removal
- LSTM encoder, repeated latent vector, LSTM decoder, time-distributed linear output
- Latent units 32; layers 1; loss mse
- Maximum epochs 15; early-stopping patience 3; batch 128
- Normal-validation quantile 0.995; threshold 3.909541; persistence 3
- Frozen SHA-256 `7e3b13fc8cb1c041422d9971a3824ccc6510b72344c1d33cff23d92cc6f2c0c4`

## Final comparison

| Method | Micro precision | Micro recall | Micro F1 | Macro precision | Macro recall | Macro F1 | Event recall | Point FPR | False alerts/1,000 | Mean delay | Median delay | P90 delay |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| threshold | 0.153255 | 0.044821 | 0.069357 | 0.069261 | 0.123174 | 0.067270 | 0.461538 | 0.035940 | 4.046660 | 86.666667 | 64.000000 | 176.500000 |
| isolation_forest | 0.432402 | 0.116025 | 0.182957 | 0.198945 | 0.145421 | 0.116458 | 0.461538 | 0.022104 | 0.626947 | 70.666667 | 66.000000 | 129.500000 |
| combined | 0.283080 | 0.156498 | 0.201564 | 0.191257 | 0.260504 | 0.160782 | 0.615385 | 0.057522 | 4.141652 | 84.375000 | 64.000000 | 179.900000 |
| lstm_autoencoder | 0.331492 | 0.008994 | 0.017513 | 0.337302 | 0.019288 | 0.035718 | 0.307692 | 0.002632 | 0.854928 | 102.750000 | 121.000000 | 142.700000 |

Per-channel winner count: `{'threshold': 3, 'isolation_forest': 3, 'combined': 1, 'lstm_autoencoder': 2}`.

## Per-channel metrics

| Mission | Channel | Method | F1 | Event recall | Point FPR | False alerts/1,000 | Mean delay | Winner |
|---|---|---|---:|---:|---:|---:|---:|---|
| MSL | F-7 | threshold | 0.170819 | 1.000000 | 0.019650 | 8.903839 | 54.333333 | isolation_forest |
| MSL | F-7 | isolation_forest | 0.450000 | 1.000000 | 0.009069 | 3.561535 | 57.666667 | isolation_forest |
| MSL | F-7 | combined | 0.439776 | 1.000000 | 0.028935 | 9.101702 | 54.333333 | isolation_forest |
| MSL | F-7 | lstm_autoencoder | 0.000000 | 0.000000 | 0.013604 | 3.363672 | — | isolation_forest |
| MSL | D-16 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| MSL | D-16 | isolation_forest | 0.569888 | 1.000000 | 0.610390 | 0.912825 | 6.000000 | isolation_forest |
| MSL | D-16 | combined | 0.569888 | 1.000000 | 0.610390 | 0.912825 | 6.000000 | isolation_forest |
| MSL | D-16 | lstm_autoencoder | 0.134670 | 1.000000 | 0.000000 | 1.825650 | 143.000000 | isolation_forest |
| MSL | F-8 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| MSL | F-8 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| MSL | F-8 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| MSL | F-8 | lstm_autoencoder | 0.018450 | 1.000000 | 0.000000 | 0.000000 | 142.000000 | lstm_autoencoder |
| MSL | M-4 | threshold | 0.392021 | 1.000000 | 0.378288 | 20.608440 | 252.000000 | threshold |
| MSL | M-4 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| MSL | M-4 | combined | 0.392021 | 1.000000 | 0.378288 | 20.608440 | 252.000000 | threshold |
| MSL | M-4 | lstm_autoencoder | 0.000000 | 0.000000 | 0.002238 | 0.490677 | — | threshold |
| SMAP | P-7 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| SMAP | P-7 | isolation_forest | 0.001210 | 1.000000 | 0.000156 | 0.123900 | 149.000000 | isolation_forest |
| SMAP | P-7 | combined | 0.001210 | 1.000000 | 0.000156 | 0.123900 | 149.000000 | isolation_forest |
| SMAP | P-7 | lstm_autoencoder | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | isolation_forest |
| SMAP | D-7 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-7 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-7 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | D-7 | lstm_autoencoder | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | G-1 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | G-1 | isolation_forest | 0.000000 | 0.000000 | 0.000599 | 0.118078 | — | threshold |
| SMAP | G-1 | combined | 0.000000 | 0.000000 | 0.000599 | 0.118078 | — | threshold |
| SMAP | G-1 | lstm_autoencoder | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | threshold |
| SMAP | E-13 | threshold | 0.042589 | 0.666667 | 0.105659 | 14.583333 | 52.500000 | combined |
| SMAP | E-13 | isolation_forest | 0.027027 | 0.333333 | 0.003343 | 1.273148 | 96.000000 | combined |
| SMAP | E-13 | combined | 0.044143 | 0.666667 | 0.106017 | 14.583333 | 52.500000 | combined |
| SMAP | E-13 | lstm_autoencoder | 0.012500 | 0.333333 | 0.006447 | 2.662037 | 100.000000 | combined |
| SMAP | B-1 | threshold | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| SMAP | B-1 | isolation_forest | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| SMAP | B-1 | combined | 0.000000 | 0.000000 | 0.000000 | 0.000000 | — | lstm_autoencoder |
| SMAP | B-1 | lstm_autoencoder | 0.155844 | 1.000000 | 0.000000 | 0.000000 | 26.000000 | lstm_autoencoder |

## Reconstruction evidence

High reconstruction error means the sequence differed from learned normal behaviour. It does not identify a confirmed root cause.
Timeline: `reports/evaluation/phase4_lstm_reconstruction_examples.svg`. JSON evidence includes thresholds, window bounds, confirmation errors, persistence, and per-feature errors.

## Runtime and artifact

- Training: 17530.356 ms
- Inference (threshold / Isolation Forest / combined / LSTM): 12.023 / 1494.009 / 1518.155 / 1889.626 ms
- Peak process working set: unavailable from the Windows process API
- Isolated environment size: 981624152 bytes
- Parameters: 12961
- Artifact: 56517 bytes; SHA-256 `4a6947a11d3f50aab968c05ebff6a10e708aec2e5e69c2a72f4873c7b6a35767`

## Phase 5 eligibility gate

- [ ] macro_f1_gain
- [ ] event_recall_not_lower
- [x] false_alert_limit
- [x] practical_inference
- [x] improvement_spans_multiple_channels

Overall: **failed**.
Do not integrate the LSTM into the live prototype. Preserve it as research evidence and retain the robust threshold baseline as the recommended operational candidate.

## False-alert and delay trade-offs

No point adjustment was used. LSTM false alerts were 0.854928/1,000 versus 4.046660 for thresholds, but event recall fell from 0.461538 to 0.307692. Median matched-event delay increased from 64.0 to 121.0 observations. This is a lower-alert, lower-sensitivity trade-off, not a win.

## Limitations

- MSL has only 4 valid unseen channels after required exclusions; requested 5.
- Telemanom telemetry is anonymized and pre-scaled upstream.
- Only primary telemetry value_0 is shared across SMAP and MSL; anonymized command inputs were excluded from the pooled model.
- Public training arrays are treated as normal because official training interval labels are unavailable.
- Synthetic validation ramps test one artificial sensitivity pattern and are not NASA anomalies.
- This frozen holdout is initial research evidence, not operational validation.

## Reproduction

```powershell
cd C:\ASTRA
.\.venv312\Scripts\python.exe -m venv .venv-dl
.\.venv-dl\Scripts\python.exe -m pip install -r backend\requirements-dl.txt
.\.venv-dl\Scripts\python.exe -m backend.evaluation.phase4_lstm search
.\.venv-dl\Scripts\python.exe -m backend.evaluation.phase4_lstm manifest
# Final holdout is one-shot and refuses overwrite.
.\.venv-dl\Scripts\python.exe -m backend.evaluation.phase4_lstm holdout
```
