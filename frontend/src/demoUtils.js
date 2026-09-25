export const PROTOTYPE_DISCLAIMER = 'Session-only ground-based decision-support prototype using simulated telemetry. It does not confirm root cause, predict failure time, or command a spacecraft.'

export function eventFilename(event) {
  return `${event.event_id}.json`
}

export function buildPrototypeEventReport({ event, missionIdentifier, scenario, review }) {
  return {
    report_type: 'ASTRA prototype event report',
    mission_identifier: missionIdentifier,
    scenario,
    event_id: event.event_id,
    timing: {
      start: event.event_start_time,
      confirmed: event.alert_confirmed_time,
      end: event.event_end_time,
      duration_observations: event.duration,
    },
    severity: event.severity,
    affected_subsystem: event.affected_subsystem,
    contributing_signals: event.contributing_channels,
    supporting_evidence: event.supporting_evidence,
    detector_status: {
      method: event.detector_method,
      threshold: event.threshold_status,
      isolation_forest: event.isolation_forest_status,
      persistence_count: event.persistence_count,
      final_decision: event.final_decision,
    },
    operator_review_state: {
      acknowledged: Boolean(review?.acknowledged),
      reviewed: Boolean(review?.reviewed),
      note: String(review?.note ?? ''),
    },
    prototype_disclaimer: PROTOTYPE_DISCLAIMER,
  }
}

export function emptyEventMessage({ hasSimulation, scenario, runComplete }) {
  if (!hasSimulation) return 'Select a scenario and start the replay to view telemetry and event evidence.'
  if (scenario === 'normal' && runComplete) return 'No persistent unusual telemetry event was detected in this simulated run.'
  return 'Telemetry replay is active. ASTRA is checking whether unusual behaviour persists.'
}
