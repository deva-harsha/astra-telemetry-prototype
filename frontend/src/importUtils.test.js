import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildInvestigationReport, eventExportProvenance, importHeaders,
  recordedSimulation, sameTimestamp, sourceResetState, validateImportFile,
} from './importUtils.js'
import { buildPrototypeEventReport } from './demoUtils.js'

const event = {
  event_id: 'ASTRA-EVT-1', status: 'active', severity: 'high', affected_subsystem: 'Power',
  event_start_time: '2026-01-01T00:10:00Z', alert_confirmed_time: '2026-01-01T00:12:00Z',
  event_end_time: null, duration: 4, contributing_channels: ['battery_voltage'],
  explanation: 'Voltage fell.', supporting_evidence: 'Four observations changed.',
  detector_method: 'Live hybrid', threshold_status: 'confirmed', isolation_forest_status: 'not_confirmed',
  persistence_count: 3, final_decision: 'persistent event confirmed',
}

const importResult = {
  compatibility: 'compatible',
  telemetry: [{ timestamp: '2026-01-01T00:00:00Z', battery_voltage: 28, risk_score: 0, health_score: 100 }],
  event: null, events: [], metrics: { processing_latency_ms: 5 },
  profile: { units: { battery_voltage: 'V' } },
  data_quality: { missing_value_count: 0 },
  import_metadata: {
    sanitized_filename: 'recorded.csv', file_hash: 'abc123', row_count: 1,
    import_time: '2026-01-01T01:00:00Z', profile_id: 'astra-sim-v1', profile_version: '1.0',
    compatibility_status: 'compatible', mission_identifier: 'MISSION-X', sampling_interval_seconds: 60,
  },
}

test('browser file limits reject empty, non-CSV and oversized inputs', () => {
  assert.match(validateImportFile(null), /Select/)
  assert.match(validateImportFile({ name: 'data.txt', size: 10 }), /Only CSV/)
  assert.match(validateImportFile({ name: 'data.csv', size: 0 }), /empty/)
  assert.match(validateImportFile({ name: 'data.csv', size: 10 * 1024 * 1024 + 1 }), /10 MB/)
  assert.equal(validateImportFile({ name: 'data.csv', size: 50 }), '')
})

test('equivalent UTC timestamp representations match during imported replay', () => {
  assert.equal(sameTimestamp('2026-01-01T00:05:00+00:00', '2026-01-01T00:05:00Z'), true)
  assert.equal(sameTimestamp('2026-01-01T00:05:00Z', '2026-01-01T00:06:00Z'), false)
  assert.equal(sameTimestamp('not-a-time', '2026-01-01T00:05:00Z'), false)
})

test('source switching clears replay, reviews, errors and upload metadata', () => {
  assert.deepEqual(sourceResetState('recorded'), {
    source: 'recorded', simulation: null, visibleCount: 0, selectedEventId: null,
    reviews: {}, error: '', importFile: null, importResult: null, importError: '',
  })
})

test('import headers carry mapping without changing file content', () => {
  const headers = importHeaders({
    file: { name: 'telemetry.csv' }, timestampColumn: 'time', missionColumn: 'mission',
    mapping: { volts: 'battery_voltage' }, unitsConfirmed: true,
  })
  assert.equal(headers['Content-Type'], 'text/csv')
  assert.equal(JSON.parse(headers['X-ASTRA-Mapping']).volts, 'battery_voltage')
  assert.equal(headers['X-ASTRA-Units-Confirmed'], 'true')
})

test('import filename metadata is safe for an HTTP header', () => {
  const headers = importHeaders({ file: { name: 'télémétrie.csv' } })
  assert.equal(headers['X-ASTRA-Filename'], 't_l_m_trie.csv')
})

test('recorded response preserves visualisation-only detector boundary', () => {
  const simulation = recordedSimulation({
    compatibility: 'visualisation_only', telemetry: [{ timestamp: '2026-01-01', x: 1 }],
    visualization_channels: ['x'], events: [{ event_id: 'fake' }], event: { event_id: 'fake' },
    metrics: { risk_score: 99 }, data_quality: {}, import_metadata: { sampling_interval_seconds: 60 },
  })
  assert.equal(simulation.metrics, null)
  assert.deepEqual(simulation.events, [])
  assert.equal(simulation.event, null)
})

test('JSON export contains bounded provenance and no full telemetry', () => {
  const provenance = eventExportProvenance(importResult)
  const report = buildPrototypeEventReport({
    event, missionIdentifier: 'MISSION-X', scenario: 'recorded_import', review: { note: 'Review' },
    telemetrySource: 'Uploaded recorded telemetry', provenance, dataQuality: importResult.data_quality,
  })
  assert.equal(report.import_provenance.sanitized_filename, 'recorded.csv')
  assert.equal(report.import_provenance.file_hash_sha256, 'abc123')
  assert.equal(report.import_provenance.mapping_profile, 'astra-sim-v1@1.0')
  assert.equal('telemetry' in report, false)
  assert.doesNotMatch(JSON.stringify(report), /battery_voltage":28/)
})

test('investigation report is escaped, complete and print friendly', () => {
  const html = buildInvestigationReport({
    event, missionIdentifier: 'MISSION-X', source: 'Uploaded recorded telemetry',
    sourceLabel: 'recorded.csv', provenance: eventExportProvenance(importResult),
    quality: importResult.data_quality, review: { acknowledged: true, reviewed: true, note: '<script>unsafe</script>' },
    generatedAt: '2026-01-01T02:00:00Z',
  })
  assert.match(html, /ASTRA prototype investigation report/)
  assert.match(html, /does not confirm root cause, predict failure or authorize spacecraft action/)
  assert.match(html, /ASTRA-EVT-1/)
  assert.match(html, /abc123/)
  assert.match(html, /@media print/)
  assert.doesNotMatch(html, /<script>unsafe<\/script>/)
  assert.match(html, /&lt;script&gt;unsafe&lt;\/script&gt;/)
})

