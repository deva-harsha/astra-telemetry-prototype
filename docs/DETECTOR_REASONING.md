# ASTRA detector reasoning

## Live pipeline

The production-compatible prototype uses fixed operating limits and an Isolation Forest as detector inputs. Trend corroboration and persistence are confirmation logic. The LSTM Autoencoder is not loaded by the production application.

## Threshold detector

An observation is a threshold candidate when any of these comparisons is true:

- `battery_temperature > 31.0`
- `payload_temperature > 33.0`
- `battery_voltage < 26.5`
- `battery_current > 3.0`

The response records each genuine crossing with its channel, measured value, comparison direction and configured limit.

## Isolation Forest

The model uses 100 estimators, contamination `0.06`, deterministic random state and one worker. For a normal API run it is fitted to rolling features from the first 60 percent of the telemetry batch. A model candidate occurs when its `decision_function` score is below `-0.04`. Lower decision scores are more unusual.

The displayed anomaly score is `clip(50 + 250 × -decision_score, 0, 100)`. It is a display index, not a probability, confidence or accuracy measure.

## Rolling features and trend corroboration

Each of the eight channels contributes its value, five-observation rolling mean, rolling standard deviation, one-observation change and five-observation slope.

- Thermal trend: battery-temperature slope and payload-temperature slope are both greater than `0.12`.
- Power trend: battery-voltage slope is below `-0.035` and battery-current slope is above `0.025`.

Trend evidence does not create an event by itself. It can corroborate an Isolation Forest candidate.

## Exact combination logic

```text
threshold_candidate = thermal_threshold OR power_threshold
isolation_candidate = isolation_decision_score < -0.04
combined_candidate = threshold_candidate OR (
    isolation_candidate AND (thermal_trend OR power_trend)
)
confirmed_combined_event = combined_candidate persists for at least 3 observations
```

Only `confirmed_combined_event` drives `is_anomaly` and event creation. Separate three-observation persistence masks for threshold and Isolation Forest candidates are retained as evidence and comparison outputs; they do not replace the hybrid decision.

## Candidate and confirmed event

A candidate is one observation satisfying the exact combined expression. The count resets to zero when the next observation is not a candidate. Confirmation begins on the third consecutive candidate. Event start is moved back two observations to the first candidate in that streak. The event continues while combined candidates continue. Event IDs, timing, severity, risk and health calculations remain unchanged.

## Synthetic comparison boundary

ASTRA-generated scenarios contain deterministic point-level fault labels and an injection start. The Comparison Lab may show fault start, first candidate, first confirmation, delay in observations, candidates before injection and whether the injected interval was detected. These values describe ASTRA-generated faults and do not represent public mission performance or operational accuracy.

## Uploaded-data boundary

Compatible `astra-sim-v1@1.0` files may show detector reasoning. Their first 60 percent is assumed to be representative normal training data; ASTRA cannot verify that assumption. Visualisation-only files receive no detector, event, risk or health conclusions. Uploaded files have no labelled ground truth, so ASTRA does not report accuracy, precision, recall, false positives or false negatives. Detector agreement does not prove correctness.

## Why the LSTM is offline

The PyTorch LSTM Autoencoder was evaluated on a separate frozen nine-channel public-data holdout. It reduced false alerts but had lower event recall, lower macro F1 and longer median matched-event delay. It failed the predeclared integration gate and is not imported, loaded or selectable in production. Phase 1C and Phase 4 use different holdouts and must not be compared directly.

## Limitations

- Detector evidence explains the implemented Boolean path; it does not confirm root cause.
- Risk and health scores are prototype heuristics, not probabilities.
- Isolation Forest does not attribute an unusual observation to a physical channel.
- The live browser progressively reveals a completed backend batch; it is not a spacecraft stream.
- Simulator results do not establish operational performance.
