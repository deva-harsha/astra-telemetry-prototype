import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPrototypeEventReport, emptyEventMessage, eventFilename } from './demoUtils.js'

const event = {
  event_id: 'EVT-001', event_start_time: '2025-01-01T00:01:00Z', alert_confirmed_time: '2025-01-01T00:03:00Z',
  event_end_time: null, duration: 4, severity: 'high', affected_subsystem: 'power',
  contributing_channels: ['battery_voltage'], supporting_evidence: 'Voltage declined.', detector_method: 'hybrid',
  threshold_status: 'triggered', isolation_forest_status: 'unusual', persistence_count: 3, final_decision: 'alert',
}

test('event export is deterministic, labelled and treats notes as plain JSON data', () => {
  const input = { event, missionIdentifier: 'ASTRA-01', scenario: 'power_fault', review: { acknowledged: true, note: '<script>alert(1)</script>' } }
  const first = buildPrototypeEventReport(input)
  const second = buildPrototypeEventReport(input)
  assert.deepEqual(first, second)
  assert.equal(first.report_type, 'ASTRA prototype event report')
  assert.equal(first.operator_review_state.note, '<script>alert(1)</script>')
  assert.equal(JSON.parse(JSON.stringify(first)).operator_review_state.note, '<script>alert(1)</script>')
  assert.equal(eventFilename(event), 'EVT-001.json')
  assert.equal('telemetry' in first, false)
})

test('empty-state copy follows replay state', () => {
  assert.match(emptyEventMessage({ hasSimulation: false, scenario: 'normal', runComplete: false }), /^Select a scenario/)
  assert.match(emptyEventMessage({ hasSimulation: true, scenario: 'normal', runComplete: true }), /^No persistent unusual/)
  assert.match(emptyEventMessage({ hasSimulation: true, scenario: 'power_fault', runComplete: false }), /^Telemetry replay is active/)
})
