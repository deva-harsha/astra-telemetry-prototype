from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Interval:
    start: int
    end: int


def group_events(mask: list[bool] | np.ndarray) -> list[Interval]:
    values = np.asarray(mask, dtype=bool)
    events: list[Interval] = []
    start: int | None = None
    for index, value in enumerate(values):
        if value and start is None:
            start = index
        if start is not None and (not value or index == len(values) - 1):
            end = index if value and index == len(values) - 1 else index - 1
            events.append(Interval(start, end))
            start = None
    return events


def _overlap_or_tolerated(detected: Interval, truth: Interval, tolerance: int) -> bool:
    # A pre-existing alert that began well before the labelled event cannot claim it.
    # Label boundaries may be imprecise, so starts within tolerance on either side match.
    return truth.start - tolerance <= detected.start <= truth.end + tolerance

def calculate_metrics(
    truths: list[np.ndarray],
    predictions: list[np.ndarray],
    tolerance: int = 0,
) -> dict[str, float | int | None]:
    if len(truths) != len(predictions):
        raise ValueError("truth and prediction run counts differ")
    tp = fp = fn = tn = 0
    truth_event_count = detected_event_count = matched_events = 0
    false_events = 0
    delays: list[int] = []
    total_observations = 0

    for truth, prediction in zip(truths, predictions, strict=True):
        truth = np.asarray(truth, dtype=bool)
        prediction = np.asarray(prediction, dtype=bool)
        if truth.shape != prediction.shape:
            raise ValueError("truth and prediction lengths differ")
        total_observations += len(truth)
        tp += int(np.sum(truth & prediction))
        fp += int(np.sum(~truth & prediction))
        fn += int(np.sum(truth & ~prediction))
        tn += int(np.sum(~truth & ~prediction))

        true_events = group_events(truth)
        detected_events = group_events(prediction)
        truth_event_count += len(true_events)
        detected_event_count += len(detected_events)
        unmatched_detected = set(range(len(detected_events)))
        for true_event in true_events:
            match = next((
                index for index in sorted(unmatched_detected)
                if _overlap_or_tolerated(detected_events[index], true_event, tolerance)
            ), None)
            if match is not None:
                unmatched_detected.remove(match)
                matched_events += 1
                # A tolerated early start is boundary uncertainty, not negative latency.
                delays.append(max(0, detected_events[match].start - true_event.start))
        false_events += len(unmatched_detected)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "point_precision": round(precision, 6),
        "point_recall": round(recall, 6),
        "point_f1": round(f1, 6),
        "event_recall": round(matched_events / truth_event_count, 6) if truth_event_count else None,
        "false_positive_observations": fp,
        "point_false_positive_rate": round(fp / (fp + tn), 6) if fp + tn else 0.0,
        "false_confirmed_events": false_events,
        "false_alerts_per_1000_observations": round(false_events * 1000 / total_observations, 6) if total_observations else 0.0,
        "missed_events": truth_event_count - matched_events,
        "mean_detection_delay_observations": round(float(np.mean(delays)), 6) if delays else None,
        "median_detection_delay_observations": round(float(np.median(delays)), 6) if delays else None,
        "maximum_detection_delay_observations": max(delays) if delays else None,
        "ground_truth_events": truth_event_count,
        "detected_events": detected_event_count,
        "evaluated_observations": total_observations,
        "evaluated_runs": len(truths),
    }


def detection_delays(
    truths: list[np.ndarray], predictions: list[np.ndarray], tolerance: int = 0,
) -> list[int]:
    """Return one non-negative delay for each uniquely matched truth event."""
    delays: list[int] = []
    for truth, prediction in zip(truths, predictions, strict=True):
        true_events = group_events(truth)
        detected_events = group_events(prediction)
        unmatched = set(range(len(detected_events)))
        for true_event in true_events:
            match = next((
                index for index in sorted(unmatched)
                if _overlap_or_tolerated(detected_events[index], true_event, tolerance)
            ), None)
            if match is not None:
                unmatched.remove(match)
                delays.append(max(0, detected_events[match].start - true_event.start))
    return delays


