export const DETECTOR_HELP = Object.freeze({
  threshold: 'Checks whether a telemetry value crosses a known operating limit.',
  isolation: 'Learns the initial normal pattern and flags observations that look unusual compared with it.',
  trend: 'Checks whether related signals and their direction of change support the candidate anomaly.',
  persistence: 'Requires unusual behaviour to continue before confirming an event.',
  hybrid: 'Combines detector evidence and confirmation rules to produce an operator-review event.',
  lstm: 'Learns to reconstruct normal telemetry sequences. Large reconstruction errors may indicate unusual behaviour.',
})

export function pipelineStages(point, unavailable = false) {
  if (unavailable) return ['Not applicable', 'Not applicable', 'Not applicable', 'Not applicable', 'Not applicable']
  const evidence = point?.detector_reasoning
  if (!evidence) return ['Waiting', 'Waiting', 'Waiting', 'Waiting', 'Waiting']
  return [
    evidence.threshold.state === 'candidate' ? 'Candidate' : 'Normal',
    evidence.isolation_forest.unusual ? 'Candidate' : 'Normal',
    evidence.trend.corroborated ? 'Supporting' : 'Normal',
    evidence.persistence.confirmed ? 'Confirmed' : evidence.persistence.current_count ? 'Candidate' : 'Normal',
    evidence.final_decision.confirmed ? 'Confirmed' : 'Normal',
  ]
}

function episodeCount(points, field) {
  let previous = false
  let count = 0
  for (const point of points) {
    const value = Boolean(field(point))
    if (value && !previous) count += 1
    previous = value
  }
  return count
}

function firstPoint(points, predicate) {
  const index = points.findIndex(predicate)
  return index < 0 ? null : { index, timestamp: points[index].timestamp }
}

function uniqueChannels(points, selector) {
  return [...new Set(points.flatMap(selector))]
}

export function detectorComparison(points = []) {
  const valid = points.filter((point) => point.detector_reasoning)
  const methods = [
    {
      id: 'threshold', label: 'Threshold only',
      candidate: (point) => point.detector_reasoning.threshold.state === 'candidate',
      confirmed: (point) => point.detector_reasoning.threshold.confirmed_by_persistence,
      channels: (point) => point.detector_reasoning.threshold.channels,
    },
    {
      id: 'isolation', label: 'Isolation Forest only',
      candidate: (point) => point.detector_reasoning.isolation_forest.unusual,
      confirmed: (point) => point.detector_reasoning.isolation_forest.confirmed_by_persistence,
      channels: () => [],
    },
    {
      id: 'hybrid', label: 'Existing Combined / Hybrid',
      candidate: (point) => point.detector_reasoning.final_decision.candidate,
      confirmed: (point) => point.detector_reasoning.final_decision.confirmed,
      channels: (point) => [
        ...point.detector_reasoning.threshold.channels,
        ...point.detector_reasoning.trend.signals.map((signal) => signal.channel),
      ],
    },
  ]
  const summaries = methods.map((method) => ({
    id: method.id,
    label: method.label,
    candidateObservations: valid.filter(method.candidate).length,
    confirmedEventCount: episodeCount(valid, method.confirmed),
    firstCandidate: firstPoint(valid, method.candidate),
    firstConfirmed: firstPoint(valid, method.confirmed),
    channels: uniqueChannels(valid.filter(method.candidate), method.channels),
  }))
  const agreement = valid.reduce((result, point) => {
    const states = methods.map((method) => method.candidate(point))
    if (states.every((value) => value === states[0])) result.agree += 1
    else result.disagree += 1
    return result
  }, { agree: 0, disagree: 0 })
  return { methods: summaries, agreement }
}

export function syntheticComparison(points = []) {
  const onset = points.findIndex((point) => point.fault_active)
  if (onset < 0) return null
  const firstCandidate = points.findIndex((point) => point.detector_reasoning?.final_decision.candidate)
  const firstConfirmed = points.findIndex((point) => point.detector_reasoning?.final_decision.confirmed)
  return {
    faultStart: { index: onset, timestamp: points[onset].timestamp },
    firstCandidate: firstCandidate < 0 ? null : { index: firstCandidate, timestamp: points[firstCandidate].timestamp },
    firstConfirmed: firstConfirmed < 0 ? null : { index: firstConfirmed, timestamp: points[firstConfirmed].timestamp },
    confirmationDelayObservations: firstConfirmed < 0 ? null : Math.max(0, firstConfirmed - onset),
    candidatesBeforeFault: points.slice(0, onset).filter((point) => point.detector_reasoning?.final_decision.candidate).length,
    injectedIntervalDetected: firstConfirmed >= onset,
  }
}
