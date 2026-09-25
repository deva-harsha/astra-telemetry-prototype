# ASTRA Phase 1B evaluation evidence

Run date: 2026-09-24

This report records executed results. ASTRA does not use live spacecraft telemetry, does not control a spacecraft, and does not confirm root cause or operational readiness.

## Commands executed

Environment and dependencies:

~~~powershell
cd C:\ASTRA
& 'C:\Users\vbitr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -r backend\requirements.txt
~~~

Verification:

~~~powershell
.\.venv312\Scripts\python.exe -m pytest backend\tests -q
cd frontend
npm run lint
npm run build
cd ..
~~~

Synthetic evaluation:

~~~powershell
.\.venv312\Scripts\python.exe -m backend.evaluation.run --config backend\evaluation\configs\default.json
~~~

Public data and limited evaluations:

~~~powershell
.\.venv312\Scripts\python.exe -m backend.data.download_telemanom
.\.venv312\Scripts\python.exe -m backend.evaluation.run --dataset telemanom --mission SMAP --limit-channels 3
.\.venv312\Scripts\python.exe -m backend.evaluation.run --dataset telemanom --mission MSL --limit-channels 3
~~~
## Runtime versions

| Component | Version |
|---|---:|
| Python | 3.12.14 |
| NumPy | 2.5.3 |
| SciPy | 1.18.1 |
| pandas | 3.0.6 |
| scikit-learn | 1.9.1 |
| FastAPI | 0.141.1 |
| Pydantic | 2.13.5 |

## Dataset sources

### Synthetic

Source: ASTRA deterministic simulator version astra-simulator-v1.

- Training: four independent normal runs, seeds 101–104, 720 observations.
- Validation: seeds 201–203, one normal, one thermal, one power run, 540 observations.
- Test: seeds 301–306, two normal, two thermal, two power runs, 1,080 observations.
- No seed appears in more than one split.
- Only the independent normal training runs fit Isolation Forest.
- Test ground truth comes from explicit injected-fault fields, not detector output.

### Public Telemanom SMAP/MSL

Repository: https://github.com/khundman/telemanom

The legacy S3 object returned HTTP 403. The downloader then used the public dataset currently referenced by the official Telemanom README:

https://www.kaggle.com/datasets/patrickfleith/nasa-anomaly-detection-dataset-smap-msl

Labels came from:

https://raw.githubusercontent.com/khundman/telemanom/master/labeled_anomalies.csv

Recorded archive SHA-256:

6084d3ee3906381f2c98aa3773b6b2d77c82413503faa78f962196582e873733

Recorded labels SHA-256:

057ce2d6c8875982bf4e5404aefea14efdcbce413d80826d2b737c95b59b7539

The extracted archive contains 413 files totalling 272,155,372 bytes. Original train and test arrays remain separate.

Evaluated subsets:

- SMAP: A-1, A-2, A-3; 24,759 test observations; 3 labelled event intervals.
- MSL: C-1, C-2, D-14; 6,940 test observations; 6 labelled event intervals.

These are anonymized, pre-scaled recorded telemetry arrays. They are not live telemetry and have no physical units or exact timestamps in ASTRA.

## Metric definitions

- Precision: confirmed anomalous observations inside ground truth divided by all confirmed anomalous observations.
- Recall: confirmed ground-truth observations divided by all anomalous ground-truth observations.
- F1: harmonic mean of point precision and recall.
- Point false-positive rate: false-positive observations divided by all normal observations.
- Event recall: labelled event intervals matched by a confirmed event.
- False alerts per 1,000 observations: unmatched confirmed event intervals divided by evaluated observations, multiplied by 1,000.
- Detection delay: confirmed event start minus ground-truth event start, in observation indices.
- Processing time: wall-clock time for the method scope documented in each JSON report. It is machine-dependent and excludes spacecraft transmission.

An event matches only if its confirmed start lies inside the labelled interval or within the configured two-observation tolerance. A long alert that began before that tolerance cannot claim a later event.

## Synthetic test results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts/1,000 | Mean delay | Processing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Threshold baseline | 1.000000 | 0.548611 | 0.708520 | 0.000000 | 1.000000 | 0.000000 | 32.5 obs | 2.017 ms |
| Isolation Forest | 1.000000 | 0.100694 | 0.182965 | 0.000000 | 0.500000 | 7.407407 | 6.0 obs | 52.415 ms |
| Combined detector | 1.000000 | 0.555556 | 0.714286 | 0.000000 | 1.000000 | 0.000000 | 32.0 obs | 87.201 ms |

Isolation Forest and combined model fitting took 109.119 ms and is reported separately from test decision time.

Perfect point precision is not evidence of a perfect detector. The injected faults occupy the final 72 observations of each fault run, while the baseline confirms roughly 32 observations after injection. Predictions therefore fall inside broad injected intervals, but recall remains around 0.55. Isolation Forest alone missed two of four events and produced eight unmatched fragmented event intervals.

The combined detector improves F1 by only 0.005766 and mean delay by 0.5 observation over thresholds. That is marginal. It does not establish meaningful ML value.

## SMAP subset results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts/1,000 | Mean delay | Processing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Robust baseline | 0.009840 | 0.222513 | 0.018847 | 0.350864 | 0.000000 | 0.040389 | — | 3.171 ms |
| Isolation Forest | 0.000000 | 0.000000 | 0.000000 | 0.000082 | 0.000000 | 0.080779 | — | 372.504 ms |
| Combined detector | 0.009838 | 0.222513 | 0.018843 | 0.350946 | 0.000000 | 0.121168 | — | 614.947 ms |

None of the three methods confirmed an event at a valid event start for these three channels. The robust baseline created one very long pre-existing alert, explaining its high point false-positive rate and zero event recall. Combining Isolation Forest added false events without improving recall.

## MSL subset results

| Method | Precision | Recall | F1 | Point FPR | Event recall | False alerts/1,000 | Mean delay | Processing |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Robust baseline | 0.174622 | 0.447094 | 0.251151 | 0.226192 | 0.666667 | 3.890490 | 5.75 obs | 2.091 ms |
| Isolation Forest | 0.473684 | 0.013413 | 0.026087 | 0.001595 | 0.333333 | 1.008646 | 4.5 obs | 451.278 ms |
| Combined detector | 0.177624 | 0.459016 | 0.256133 | 0.227468 | 0.833333 | 4.610951 | 13.2 obs | 446.523 ms |

The combined detector raises event recall from 0.667 to 0.833 and point F1 from 0.251 to 0.256. It also produces more false confirmed events and a longer mean delay. This is a trade-off, not an unqualified improvement.

## Verification results

- Backend: 22 tests passed.
- Frontend lint: passed.
- Frontend production build: passed.
- Vite reported the existing large-chunk warning; the build succeeded.
- Python source compilation: passed.
- Git diff whitespace check: passed after final cleanup.

Two TestClient deprecation warnings remain in the backend test run. They do not fail tests.

## Bugs fixed during Phase 1B

1. Converted Pandas NaN ground-truth event identifiers to null at the API serialization boundary.
2. Added point false-positive rate rather than using false alerts per 1,000 as a substitute.
3. Prevented long pre-existing alerts from claiming later labelled events and creating negative detection delays.
4. Measured method-specific decision time rather than assigning one shared duration to every method.
5. Preserved separate synthetic, SMAP and MSL JSON/CSV reports.
6. Added the current official Telemanom README dataset source as a fallback after the legacy S3 object returned HTTP 403.
7. Repaired Windows PowerShell command paths that had been corrupted by escaped backslashes in generated documentation.

## Failures and limitations

- The Microsoft Store Python launcher and a separate local Python installation were denied by Windows policy.
- A clean environment created from the permitted bundled Python runtime solved the earlier scikit-learn DLL failure.
- The legacy Telemanom S3 object returned HTTP 403.
- Only three SMAP and three MSL channels were evaluated.
- Public telemetry is anonymized and pre-scaled.
- The robust baseline threshold and Isolation Forest parameters have not been tuned on a broader validation set.
- The small public subsets are insufficient for mission-level performance claims.
- Processing times depend on this machine and run.
- Persistence is common to all three decisions; it does not explain the combined method's slight synthetic gain because each method is evaluated after the same three-observation rule.
- ASTRA does not diagnose root cause or control spacecraft.

## Recommended next phase

Use validation data only to calibrate the public robust threshold, Isolation Forest decision threshold and persistence length. Expand evaluation channel-by-channel, retain per-channel metrics, and inspect each false alert before selecting one configuration. Keep the final test channels untouched until those choices are fixed. Do not add another model until the combined detector demonstrates a consistent benefit over the baseline.


