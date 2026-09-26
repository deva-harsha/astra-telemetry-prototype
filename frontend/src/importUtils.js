export const MAX_IMPORT_BYTES = 10 * 1024 * 1024
export const INVESTIGATION_DISCLAIMER = 'ASTRA prototype investigation report. This report provides anomaly evidence for human review and does not confirm root cause, predict failure or authorize spacecraft action.'

export function validateImportFile(file) {
  if (!file) return 'Select a CSV file.'
  if (!String(file.name ?? '').toLowerCase().endsWith('.csv')) return 'Only CSV files are accepted.'
  if (!file.size) return 'The CSV file is empty.'
  if (file.size > MAX_IMPORT_BYTES) return 'The CSV exceeds the 10 MB upload limit.'
  return ''
}

export function sameTimestamp(left, right) {
  if (!left || !right) return false
  const leftTime = new Date(left).getTime()
  const rightTime = new Date(right).getTime()
  return Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime === rightTime
}

export function sourceResetState(source) {
  return {
    source,
    simulation: null,
    visibleCount: 0,
    selectedEventId: null,
    reviews: {},
    error: '',
    importFile: null,
    importResult: null,
    importError: '',
  }
}

export function importHeaders({ file, timestampColumn, missionColumn, mapping, unitsConfirmed }) {
  const safeHeaderFilename = String(file?.name ?? 'recorded-telemetry.csv')
    .replace(/[^ -~]/g, '_')
    .slice(0, 180)
  const headers = {
    'Content-Type': 'text/csv',
    'X-ASTRA-Filename': safeHeaderFilename,
  }
  if (timestampColumn) headers['X-ASTRA-Timestamp-Column'] = timestampColumn
  if (missionColumn) headers['X-ASTRA-Mission-Column'] = missionColumn
  if (mapping && Object.keys(mapping).length) headers['X-ASTRA-Mapping'] = JSON.stringify(mapping)
  if (unitsConfirmed) headers['X-ASTRA-Units-Confirmed'] = 'true'
  return headers
}

export function recordedSimulation(result) {
  if (!result || result.compatibility === 'invalid') return null
  const compatible = result.compatibility === 'compatible'
  return {
    ...result,
    metadata: {
      scenario: 'recorded_import',
      points: result.telemetry.length,
      source: 'Uploaded recorded telemetry',
      units: compatible ? result.profile.units : {},
      interval_seconds: result.import_metadata.sampling_interval_seconds,
      fault_start_index: null,
      fault_start_timestamp: null,
      import_metadata: result.import_metadata,
    },
    data_quality: result.data_quality,
    metrics: compatible ? result.metrics : null,
    event: compatible ? result.event : null,
    events: compatible ? result.events : [],
  }
}

export function eventExportProvenance(result) {
  if (!result?.import_metadata) return null
  const metadata = result.import_metadata
  return {
    sanitized_filename: metadata.sanitized_filename,
    file_hash_sha256: metadata.file_hash,
    row_count: metadata.row_count,
    import_time: metadata.import_time,
    mapping_profile: metadata.profile_id ? `${metadata.profile_id}@${metadata.profile_version}` : null,
    compatibility_status: metadata.compatibility_status,
  }
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function field(label, value) {
  return `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? '—')}</dd></div>`
}

export function buildInvestigationReport({ event, missionIdentifier, source, sourceLabel, provenance, quality, review, generatedAt }) {
  const generated = generatedAt ?? new Date().toISOString()
  const evidence = [
    field('Detector method', event.detector_method),
    field('Threshold status', event.threshold_status),
    field('Isolation Forest status', event.isolation_forest_status),
    field('Persistence', `${event.persistence_count} consecutive observations`),
    field('Final decision', event.final_decision),
  ].join('')
  const qualityText = quality
    ? `Missing values: ${quality.missing_value_count ?? 0}; duplicate timestamps: ${quality.duplicate_timestamp_count ?? 0}; out-of-order timestamps: ${quality.out_of_order_timestamp_count ?? 0}; estimated gaps: ${quality.estimated_gap_count ?? quality.telemetry_gap_count ?? 0}.`
    : 'No data-quality summary available.'
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>ASTRA investigation report — ${escapeHtml(event.event_id)}</title>
<style>
  :root{font-family:Arial,sans-serif;color:#111;background:#fff}body{max-width:900px;margin:0 auto;padding:36px}
  header{border-bottom:3px solid #111;padding-bottom:18px}h1{font-size:28px;margin:0 0 8px}h2{font-size:14px;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid #aaa;padding-bottom:6px;margin-top:28px}
  .disclaimer{border:1px solid #555;padding:12px;font-size:12px;line-height:1.5}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:0 24px}dl{margin:0}.grid div{border-bottom:1px solid #ddd;padding:9px 0}dt{font-size:10px;text-transform:uppercase;color:#555}dd{margin:4px 0 0;font-size:12px;overflow-wrap:anywhere}p,li{font-size:12px;line-height:1.55}.mono{font-family:Consolas,monospace}
  @media(max-width:600px){body{padding:18px}.grid{grid-template-columns:1fr}}
  @media print{body{max-width:none;padding:0}button{display:none}@page{margin:16mm}}
</style></head><body>
<header><h1>ASTRA Prototype Investigation Report</h1><p class="disclaimer">${escapeHtml(INVESTIGATION_DISCLAIMER)}</p></header>
<h2>Mission and source</h2><dl class="grid">
${field('Mission identifier', missionIdentifier)}
${field('Telemetry source', source)}
${field('Scenario or file', sourceLabel)}
${field('File hash SHA-256', provenance?.file_hash_sha256)}
${field('Profile identifier', provenance?.mapping_profile)}
${field('Compatibility', provenance?.compatibility_status ?? 'Simulated telemetry demonstration')}
</dl>
<h2>Event</h2><dl class="grid">
${field('Event ID', event.event_id)}
${field('Event state', event.status)}
${field('Severity', event.severity)}
${field('Subsystem', event.affected_subsystem)}
${field('Event start', event.event_start_time)}
${field('Confirmation time', event.alert_confirmed_time)}
${field('Duration', `${event.duration} observations`)}
${field('Contributing channels', event.contributing_channels.join(', '))}
</dl>
<h2>What changed</h2><p>${escapeHtml(event.explanation)}</p>
<h2>Supporting evidence</h2><p>${escapeHtml(event.supporting_evidence)}</p>
<h2>Detector evidence</h2><dl class="grid">${evidence}</dl>
<h2>Data quality</h2><p>${escapeHtml(qualityText)}</p>
<h2>Operator review</h2><dl class="grid">
${field('Acknowledged', review?.acknowledged ? 'Yes' : 'No')}
${field('Review status', review?.reviewed ? 'Reviewed' : 'Pending')}
${field('Operator note', review?.note ?? '')}
${field('Generated timestamp', generated)}
</dl>
<h2>Limitations</h2><ul><li>Anomaly evidence does not confirm root cause.</li><li>Risk and health indicators are prototype heuristics.</li><li>Recorded import compatibility is not operational spacecraft qualification.</li><li>This report does not authorize spacecraft action.</li></ul>
</body></html>`
}

