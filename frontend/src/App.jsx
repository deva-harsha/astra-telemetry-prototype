import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, CirclePause, CirclePlay, Download, FileUp, Printer, RotateCcw } from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import validationEvidence from './validationEvidence.json'
import { buildPrototypeEventReport, emptyEventMessage, eventFilename } from './demoUtils.js'
import {
  buildInvestigationReport, eventExportProvenance, importHeaders,
  recordedSimulation, sameTimestamp, sourceResetState, validateImportFile,
} from './importUtils.js'
import './App.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
const TOTAL_POINTS = 180
const SEED = 42
const HEALTH_RETRY_MS = 5000
const HEALTH_TIMEOUT_MS = 90000
const SIMULATION_TIMEOUT_MS = 45000
const MISSION_ID = 'ASTRA-01'
const WORKFLOW_STAGES = ['Receive telemetry', 'Analyse patterns', 'Confirm anomaly', 'Explain alert']

const SCENARIOS = [
  { id: 'normal', label: 'Normal Operation', description: 'Control run containing no injected fault.' },
  { id: 'thermal_fault', label: 'Thermal Fault', description: 'Simulates gradual abnormal heating across related subsystems.' },
  { id: 'power_fault', label: 'Power Fault', description: 'Simulates unusual voltage and current behaviour.' },
]

const CHANNELS = {
  battery_voltage: { label: 'Battery voltage', unit: 'V', low: 26.5, high: 29.5 },
  battery_current: { label: 'Battery current', unit: 'A', low: 1.8, high: 3.0 },
  battery_temperature: { label: 'Battery temperature', unit: '°C', low: 18, high: 31 },
  signal_strength: { label: 'Signal strength', unit: 'dBm', low: -90, high: -76 },
  attitude_error: { label: 'Attitude error', unit: '°', low: 0, high: 0.5 },
  payload_temperature: { label: 'Payload temperature', unit: '°C', low: 20, high: 33 },
  propulsion_pressure: { label: 'Propulsion pressure', unit: 'kPa', low: 205, high: 215 },
  radiation_level: { label: 'Radiation level', unit: 'mGy/h', low: 0, high: 0.25 },
}

const SUBSYSTEMS = [
  { id: 'power', label: 'Power & Thermal', keys: ['battery_voltage', 'battery_current', 'battery_temperature'] },
  { id: 'communication', label: 'Communication', keys: ['signal_strength'] },
  { id: 'attitude', label: 'Attitude', keys: ['attitude_error'] },
  { id: 'payload', label: 'Payload & Propulsion', keys: ['payload_temperature', 'propulsion_pressure'] },
  { id: 'environment', label: 'Environment', keys: ['radiation_level'] },
]

const SPEEDS = [
  { label: '0.5×', ms: 300 }, { label: '1×', ms: 150 },
  { label: '2×', ms: 75 }, { label: '4×', ms: 35 },
]
const LINE_COLORS = ['#f4f3ee', '#a3a3a3', '#737373']
const LINE_DASHES = [undefined, '6 4', '2 4']

function timeLabel(value) {
  if (!value) return '—'
  return `${new Date(value).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })} UTC`
}

function reading(key, value) {
  if (value == null) return '—'
  const digits = key === 'radiation_level' ? 3 : key === 'attitude_error' ? 2 : 1
  return `${Number(value).toFixed(digits)} ${CHANNELS[key].unit}`
}

function runAnalysisTime(milliseconds) {
  if (milliseconds == null) return '—'
  return milliseconds >= 1000 ? `${(milliseconds / 1000).toFixed(2)} s/run` : `${milliseconds.toFixed(1)} ms/run`
}

function timePerObservation(milliseconds, observations) {
  if (milliseconds == null || !observations) return '—'
  return `≈${(milliseconds / observations).toFixed(1)} ms/observation`
}

function trend(key, current, prior) {
  if (current == null || prior == null) return '—'
  const delta = current - prior
  const width = CHANNELS[key].high - CHANNELS[key].low
  if (delta > width * 0.03) return 'Rising ↗'
  if (delta < -width * 0.03) return 'Falling ↘'
  return 'Stable →'
}

function eventStatusClass(event, review) {
  if (review?.acknowledged) return 'event-acknowledged'
  if (event.status === 'resolved' || review?.reviewed) return 'event-resolved'
  return event.severity === 'high' ? 'event-high' : 'event-review'
}

function derivedQuality(simulation) {
  if (!simulation) return null
  if (simulation.data_quality) return simulation.data_quality
  const timestamps = simulation.telemetry.map((point) => new Date(point.timestamp).getTime())
  const deltas = timestamps.slice(1).map((value, index) => (value - timestamps[index]) / 1000)
  return {
    timestamp_continuity: deltas.every((value) => value === 60),
    missing_value_count: simulation.telemetry.reduce((count, point) => count + Object.keys(CHANNELS).filter((key) => point[key] == null).length, 0),
    telemetry_gap_count: deltas.filter((value) => value > 60).length,
    stale_observation_count: deltas.filter((value) => value <= 0).length,
    available_channels: Object.keys(CHANNELS).length,
    data_source: simulation.metadata.source,
  }
}

function TelemetryChart({ data, subsystem, event, faultStartTime }) {
  const chartData = useMemo(() => data.map((point) => {
    const scaled = { timestamp: point.timestamp }
    subsystem.keys.forEach((key) => {
      const channel = CHANNELS[key]
      const middle = (channel.low + channel.high) / 2
      scaled[key] = (point[key] - middle) / ((channel.high - channel.low) / 2)
      scaled[`raw_${key}`] = point[key]
    })
    return scaled
  }), [data, subsystem])

  const matchingTimestamp = (value) => data.find((point) => sameTimestamp(point.timestamp, value))?.timestamp ?? null
  const faultTime = matchingTimestamp(faultStartTime)
  const eventTime = matchingTimestamp(event?.event_start_time)
  const detectionTime = matchingTimestamp(event?.alert_confirmed_time)
  const eventEnd = matchingTimestamp(event?.event_end_time) ?? (eventTime && data.at(-1)?.timestamp)
  const eventColor = event?.severity === 'high' ? '#cf8278' : '#c7a16d'

  return <div className="chart-frame" role="img" aria-label={`${subsystem.label} normalized telemetry comparison chart`}>
    {data.length === 0 ? <div className="chart-empty"><span>Telemetry plot ready</span><p>Start a simulation to reveal the mission replay.</p></div> :
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 24, right: 18, left: 0, bottom: 6 }}>
          <CartesianGrid stroke="#292929" strokeDasharray="2 5" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={timeLabel} minTickGap={50} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={{ stroke: '#343434' }} tickLine={false} />
          <YAxis domain={['auto', 'auto']} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={false} tickLine={false} width={38} />
          <Tooltip labelFormatter={timeLabel} formatter={(value, name, item) => [reading(item.dataKey, item.payload[`raw_${item.dataKey}`]), name]} contentStyle={{ background: '#171717', border: '1px solid #3a3a3a', borderRadius: 2, color: '#f4f3ee', fontSize: 12 }} labelStyle={{ color: '#a3a3a3', marginBottom: 8 }} />
          {eventTime && eventEnd && <ReferenceArea x1={eventTime} x2={eventEnd} fill={event?.severity === 'high' ? '#a9534c' : '#b48b50'} fillOpacity={0.12} strokeOpacity={0} />}
          {faultTime && <ReferenceLine x={faultTime} stroke="#b48b50" strokeDasharray="4 4" label={{ value: 'Fault injected', position: 'insideTopRight', fill: '#c7a677', fontSize: 10 }} />}
          {detectionTime && <ReferenceLine x={detectionTime} stroke="#b66d62" strokeDasharray="2 3" label={{ value: 'Alert confirmed', position: 'insideTopLeft', fill: '#d19489', fontSize: 10 }} />}
          {subsystem.keys.map((key, index) => { const contributes = event?.contributing_channels?.includes(key); return <Line key={key} type="monotone" dataKey={key} name={CHANNELS[key].label} stroke={contributes ? eventColor : LINE_COLORS[index]} strokeOpacity={event && !contributes ? 0.35 : 1} strokeWidth={contributes ? 2.5 : index === 0 ? 2 : 1.6} strokeDasharray={LINE_DASHES[index]} dot={false} activeDot={{ r: 3 }} isAnimationActive={false} /> })}
        </LineChart>
      </ResponsiveContainer>}
  </div>
}

function ImportedTelemetryChart({ data, channels }) {
  const visibleChannels = useMemo(() => channels.slice(0, 3), [channels])
  const chartData = useMemo(() => {
    const bounds = Object.fromEntries(visibleChannels.map((channel) => {
      const values = data.map((point) => point[channel]).filter(Number.isFinite)
      return [channel, { min: Math.min(...values), max: Math.max(...values) }]
    }))
    return data.map((point) => {
      const scaled = { timestamp: point.timestamp }
      visibleChannels.forEach((channel) => {
        const value = point[channel]
        const { min, max } = bounds[channel]
        scaled[channel] = Number.isFinite(value) ? (max === min ? 0 : ((value - min) / (max - min)) * 2 - 1) : null
        scaled[`raw_${channel}`] = value
      })
      return scaled
    })
  }, [data, visibleChannels])
  return <div className="chart-frame" role="img" aria-label="Uploaded telemetry normalized visualisation">
    {!data.length ? <div className="chart-empty"><span>Recorded telemetry ready</span><p>Start replay to reveal uploaded observations.</p></div> :
      <ResponsiveContainer width="100%" height="100%"><LineChart data={chartData} margin={{ top: 24, right: 18, left: 0, bottom: 6 }}>
        <CartesianGrid stroke="#292929" strokeDasharray="2 5" vertical={false} />
        <XAxis dataKey="timestamp" tickFormatter={timeLabel} minTickGap={50} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={{ stroke: '#343434' }} tickLine={false} />
        <YAxis domain={[-1, 1]} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={false} tickLine={false} width={38} />
        <Tooltip labelFormatter={timeLabel} formatter={(value, name, item) => [item.payload[`raw_${item.dataKey}`] ?? 'Missing', name]} contentStyle={{ background: '#171717', border: '1px solid #3a3a3a', borderRadius: 2, color: '#f4f3ee', fontSize: 12 }} />
        {visibleChannels.map((channel, index) => <Line key={channel} type="monotone" dataKey={channel} name={channel} stroke={LINE_COLORS[index]} strokeWidth={index === 0 ? 2 : 1.6} strokeDasharray={LINE_DASHES[index]} dot={false} isAnimationActive={false} />)}
      </LineChart></ResponsiveContainer>}
  </div>
}

function EventList({ events, selectedId, reviews, onSelect }) {
  return <section className="event-list-section" aria-labelledby="event-list-title">
    <div className="event-list-heading"><h3 id="event-list-title">Confirmed events</h3><span>{String(events.length).padStart(2, '0')}</span></div>
    {events.length === 0 ? <p className="event-list-empty">No confirmed events in the visible replay.</p> : <ol className="event-list">
      {events.map((event) => <li key={event.event_id}><button type="button" className={`${selectedId === event.event_id ? 'selected' : ''} ${eventStatusClass(event, reviews[event.event_id])}`} onClick={() => onSelect(event)}><span className="event-list-dot" /><span><strong>{event.title}</strong><small>{timeLabel(event.event_start_time)} · {event.status} · {event.duration} observations</small></span><em>{event.severity}</em></button></li>)}
    </ol>}
  </section>
}

function EventReview({ event, faultStartTime, review, onReviewChange, onExport, onReport, justConfirmed, emptyMessage }) {
  if (!event) return <div className="empty-event"><div className="empty-rule" /><h3>No selected event</h3><p>{emptyMessage}</p><small>Confirmed events will appear above for operator review.</small></div>
  const detectionDelay = faultStartTime && event.alert_confirmed_time
    ? Math.max(0, Math.round((new Date(event.alert_confirmed_time) - new Date(faultStartTime)) / 60000))
    : null
  return <div className={`event-content ${justConfirmed ? `alert-arrival severity-${event.severity}` : ''}`}>
    <div className="event-state"><span className={`severity-label severity-${event.severity}`}>{event.severity} severity</span><span>{review?.acknowledged ? 'Acknowledged' : review?.reviewed ? 'Reviewed' : event.status}</span></div>
    <section className="review-section detection-summary"><h4>What changed</h4><h3>{event.title}</h3><p>{event.explanation}</p><dl className="event-fields"><div><dt>Event ID</dt><dd>{event.event_id}</dd></div><div><dt>Affected subsystem</dt><dd>{event.affected_subsystem}</dd></div><div><dt>Start</dt><dd>{timeLabel(event.event_start_time)}</dd></div><div><dt>End state</dt><dd>{event.event_end_time ? timeLabel(event.event_end_time) : 'Active at end of replay'}</dd></div><div><dt>Duration</dt><dd>{event.duration} observations</dd></div></dl></section>
    <section className="review-section"><h4>Supporting signals</h4><p>{event.contributing_channels.length ? event.contributing_channels.map((key) => CHANNELS[key]?.label ?? key).join(', ') : 'No subsystem channel attribution available.'}</p><p className="supporting-evidence">{event.supporting_evidence}</p></section>
    <section className="review-section"><h4>Timeline</h4><ol className="event-timeline"><li><span>Fault or unusual behaviour begins</span><time>{timeLabel(faultStartTime ?? event.event_start_time)}</time></li><li><span>Alert confirmation</span><time>{timeLabel(event.alert_confirmed_time)}</time></li><li><span>Event duration</span><time>{event.duration} observations</time></li></ol>{detectionDelay != null && <p className="detection-delay">Detection delay: {detectionDelay} min simulated mission time</p>}</section>
    <section className="review-section"><h4>Detector evidence</h4><dl className="event-fields"><div><dt>Threshold status</dt><dd>{event.threshold_status}</dd></div><div><dt>Isolation Forest status</dt><dd>{event.isolation_forest_status}</dd></div><div><dt>Persistence</dt><dd>{event.persistence_count} consecutive observations</dd></div><div><dt>Final prototype decision</dt><dd>{event.final_decision}</dd></div></dl><p className="persistence-note">Isolation Forest indicates an unusual pattern; it does not prove root cause.</p></section>
    <section className="review-section operator-actions"><h4>Operator action</h4><p>{event.operator_review_message}</p><div className="session-label">Prototype session only · not stored permanently</div><textarea aria-label="Operator note" value={review?.note ?? ''} maxLength={280} placeholder="Add a short local-session note" onChange={(changeEvent) => onReviewChange({ note: changeEvent.target.value })} /><div className="review-buttons"><button type="button" onClick={() => onReviewChange({ acknowledged: true })}>Acknowledge</button><button type="button" onClick={() => onReviewChange({ reviewed: true })}><Check size={13} />Mark reviewed</button><button type="button" onClick={() => onReviewChange(null)}>Reset review</button><button type="button" onClick={onExport}><Download size={13} />Export JSON</button><button type="button" onClick={onReport}><Printer size={13} />Print Report</button></div></section>
  </div>
}

function DataQuality({ quality }) {
  const item = (label, value, good = true) => <div><dt>{label}</dt><dd className={good ? 'quality-good' : 'quality-review'}>{value}</dd></div>
  return <section className="data-quality" aria-labelledby="quality-title"><div><span className="kicker">Input integrity</span><h2 id="quality-title">Data quality</h2><p>File warnings and communication gaps are data-quality findings. They are not spacecraft anomalies.</p></div>{quality ? <dl>{item('Timestamp continuity', quality.timestamp_continuity ? 'Continuous' : 'Review required', quality.timestamp_continuity)}{item('Missing values', quality.missing_value_count, quality.missing_value_count === 0)}{item('Telemetry gaps', quality.estimated_gap_count ?? quality.telemetry_gap_count ?? 0, !(quality.estimated_gap_count ?? quality.telemetry_gap_count ?? 0))}{item('Duplicate timestamps', quality.duplicate_timestamp_count ?? 0, !(quality.duplicate_timestamp_count ?? 0))}{item('Out-of-order', quality.out_of_order_timestamp_count ?? quality.stale_observation_count ?? 0, !(quality.out_of_order_timestamp_count ?? quality.stale_observation_count ?? 0))}{item('Constant channels', quality.constant_channels?.length ? quality.constant_channels.join(', ') : 'None', !quality.constant_channels?.length)}</dl> : <p className="quality-empty">Awaiting a simulation response.</p>}</section>
}

function ImportPanel({ file, result, error, busy, timestampColumn, missionColumn, mapping, unitsConfirmed, onFile, onDemo, onTimestamp, onMission, onMapping, onUnits, onValidate }) {
  const metadata = result?.import_metadata
  const quality = result?.data_quality
  return <section className="import-panel" aria-labelledby="import-title">
    <div className="import-heading"><div><span className="kicker">Recorded telemetry import prototype</span><h2 id="import-title">Upload, validate and map</h2></div><ol><li>Upload</li><li>Validate and map</li><li>Preview</li><li>Replay</li><li>Review and report</li></ol></div>
    <div className="import-grid"><div className="upload-card"><label className="file-control"><FileUp size={16} /><span>{file ? result?.import_metadata?.sanitized_filename ?? file.name.replace(/[^A-Za-z0-9._ -]/g, '_') : 'Choose recorded telemetry CSV'}</span><input type="file" accept=".csv,text/csv" onChange={(event) => onFile(event.target.files?.[0] ?? null)} /></label><p>Files stay in memory for this browser session and are sent only to the configured ASTRA backend.</p><div className="template-links"><a href="/examples/astra-compatible-template.csv" download>Download CSV template</a><a href="/examples/astra-normal-demo.csv" download>Download normal demo</a><a href="/examples/astra-power-fault-demo.csv" download>Download fault demo</a><button type="button" onClick={() => onDemo('astra-normal-demo.csv')} disabled={busy}>Load normal demo</button><button type="button" onClick={() => onDemo('astra-power-fault-demo.csv')} disabled={busy}>Load fault demo</button></div><small>ASTRA-generated demonstration data. Use this template to format recorded telemetry for the ASTRA prototype. Import compatibility does not represent operational spacecraft qualification.</small></div>
      <div className="compatibility-card" aria-live="polite"><span>Detector compatibility</span><strong className={`compatibility-${result?.compatibility ?? 'pending'}`}>{result?.compatibility_label ?? (result?.compatibility === 'invalid' ? 'Invalid' : 'Awaiting file')}</strong><p>{result?.compatibility === 'visualisation_only' ? 'Detection disabled because this dataset does not match a validated ASTRA prototype profile.' : result?.compatibility === 'compatible' ? 'Eligible for the existing prototype detector under astra-sim-v1.' : 'Upload a file to check compatibility.'}</p></div></div>
    {error && <div className="import-error" role="alert"><strong>File validation</strong><p>{error}</p></div>}
    {result && <><div className="mapping-panel"><div><h3>Schema mapping</h3><p>Map file columns to the one supported prototype profile. Unknown or partial mappings remain visualisation-only.</p><p>The detector trains on the first 60% of the file, assumed to be representative normal telemetry. ASTRA cannot verify that assumption.</p><p>{result.profile && Object.entries(result.profile.units).map(([channel, unit]) => channel + ": " + unit).join(" · ")}</p></div><div className="mapping-controls"><label>Timestamp column<select value={timestampColumn} onChange={(event) => onTimestamp(event.target.value)}>{result.columns.map((column) => <option key={column}>{column}</option>)}</select></label><label>Mission identifier<select value={missionColumn} onChange={(event) => onMission(event.target.value)}><option value="">Not available</option>{result.columns.map((column) => <option key={column}>{column}</option>)}</select></label>{result.numeric_columns?.map((column) => <label key={column}>{column}<select value={mapping[column] ?? ''} onChange={(event) => onMapping(column, event.target.value)}><option value="">Visualise only</option>{result.canonical_channels.map((channel) => <option key={channel} value={channel}>{channel}</option>)}</select></label>)}</div><label className="units-confirmation"><input type="checkbox" checked={unitsConfirmed} onChange={(event) => onUnits(event.target.checked)} />I confirm mapped values use the profile units shown in the import format documentation.</label><button type="button" onClick={onValidate} disabled={!file || busy}>{busy ? 'Validating…' : 'Validate mapping'}</button></div>
      {metadata && <div className="import-summary"><dl><div><dt>Sanitized filename</dt><dd>{metadata.sanitized_filename}</dd></div><div><dt>File size</dt><dd>{metadata.file_size_bytes.toLocaleString()} bytes</dd></div><div><dt>Rows</dt><dd>{metadata.row_count.toLocaleString()}</dd></div><div><dt>Start</dt><dd>{metadata.start_timestamp ?? '—'}</dd></div><div><dt>End</dt><dd>{metadata.end_timestamp ?? '—'}</dd></div><div><dt>Duration</dt><dd>{metadata.duration_seconds != null ? `${metadata.duration_seconds} s` : '—'}</dd></div><div><dt>Sampling interval</dt><dd>{metadata.sampling_interval_seconds != null ? `${metadata.sampling_interval_seconds} s` : '—'}</dd></div><div><dt>Numeric channels</dt><dd>{metadata.detected_numeric_channels?.join(', ') ?? '—'}</dd></div><div><dt>Mapped channels</dt><dd>{Object.keys(metadata.mapped_channels ?? {}).length}</dd></div><div><dt>Missing values</dt><dd>{quality?.missing_value_count ?? '—'}</dd></div><div><dt>Duplicate timestamps</dt><dd>{quality?.duplicate_timestamp_count ?? '—'}</dd></div><div><dt>Out of order</dt><dd>{quality?.out_of_order_timestamp_count ?? '—'}</dd></div><div><dt>Estimated gaps</dt><dd>{quality?.estimated_gap_count ?? '—'}</dd></div><div><dt>Constant channels</dt><dd>{quality?.constant_channels?.join(', ') || 'None'}</dd></div></dl></div>}
      {!!result.validation?.warnings?.length && <div className="import-warnings"><strong>Data-quality and compatibility findings</strong><ul>{result.validation.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      {!!result.preview?.length && <div className="preview-panel"><div><h3>Preview</h3><span>First {result.preview.length} rows only</span></div><div className="table-scroll"><table><thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.preview.map((row, index) => <tr key={index}>{result.columns.map((column) => <td key={column}>{row[column]}</td>)}</tr>)}</tbody></table></div></div>}</>}
  </section>
}

function ValidationEvidence() {
  const baseline = validationEvidence.phase1c
  const deepLearning = validationEvidence.phase4
  return <details className="validation-evidence">
    <summary><span><small>Public-data research evaluation</small>Validation evidence</span><strong>View details</strong></summary>
    <div className="validation-body">
      <p className="holdout-notice">{validationEvidence.holdout_notice}</p>
      <section className="evidence-phase" aria-labelledby="phase1c-heading">
        <div className="evidence-heading"><div><span>Frozen public-data benchmark</span><h3 id="phase1c-heading">{baseline.label}</h3></div><em className="status-chip status-research">Offline research</em></div>
        <div className="validation-stats"><span><strong>{baseline.summary.backend_tests_passed}</strong> backend tests passed at freeze</span><span><strong>{baseline.summary.public_channels_loaded}</strong> public channels loaded</span><span><strong>{baseline.summary.approaches_compared}</strong> approaches compared</span><span><strong>{baseline.summary.development_channels}</strong> development channels</span><span><strong>{baseline.summary.holdout_channels}</strong> unseen holdout channels</span><span><strong>{baseline.summary.frozen_configuration.slice(0, 12)}</strong> frozen config</span></div>
        <div className="table-scroll"><table><thead><tr><th>Method</th><th>Micro F1</th><th>Macro F1</th><th>Event recall</th><th>Point FPR</th><th>False alerts/1,000</th></tr></thead><tbody>{baseline.methods.map((method) => <tr key={method.method}><td>{method.method}</td><td>{method.micro_f1.toFixed(6)}</td><td>{method.macro_f1.toFixed(6)}</td><td>{method.event_recall.toFixed(6)}</td><td>{method.point_fpr.toFixed(6)}</td><td>{method.false_alerts_per_1000.toFixed(6)}</td></tr>)}</tbody></table></div>
        <p className="validation-conclusion">{baseline.conclusion}</p><p>{baseline.disclaimer}</p><ul>{baseline.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul><small>Source: {baseline.source}</small>
      </section>
      <section className="evidence-phase phase4-evidence" aria-labelledby="phase4-heading">
        <div className="evidence-heading"><div><span>Completed model-selection experiment</span><h3 id="phase4-heading">{deepLearning.label}</h3></div><em className="status-chip status-experimental">{deepLearning.experiment.status}</em></div>
        <dl className="experiment-facts"><div><dt>Model</dt><dd>{deepLearning.experiment.model}</dd></div><div><dt>Framework</dt><dd>{deepLearning.experiment.framework}</dd></div><div><dt>Parameters</dt><dd>{deepLearning.experiment.parameters.toLocaleString()}</dd></div><div><dt>Input window</dt><dd>{deepLearning.experiment.input_window} observations</dd></div><div><dt>Feature</dt><dd>{deepLearning.experiment.feature}</dd></div><div><dt>Evaluation</dt><dd>{deepLearning.experiment.evaluation}</dd></div><div><dt>Frozen config</dt><dd>{deepLearning.experiment.frozen_configuration.slice(0, 12)}</dd></div></dl>
        <h4>Same-holdout comparison</h4>
        <div className="table-scroll"><table><thead><tr><th>Method</th><th>Macro F1</th><th>Event recall</th><th>False alerts/1,000</th><th>Median delay</th></tr></thead><tbody>{deepLearning.methods.map((method) => <tr key={method.method}><td>{method.method}</td><td>{method.macro_f1.toFixed(6)}</td><td>{method.event_recall.toFixed(6)}</td><td>{method.false_alerts_per_1000.toFixed(6)}</td><td>{method.median_delay} observations</td></tr>)}</tbody></table></div>
        <div className="gate-panel"><h4>Predeclared integration gate</h4><ul>{deepLearning.gates.map((gate) => <li key={gate.key}><span>{gate.label}</span><strong className={gate.passed ? 'gate-passed' : 'gate-failed'}>{gate.passed ? 'Passed' : 'Failed'}</strong></li>)}<li className="gate-overall"><span>Overall integration decision</span><strong className={deepLearning.overall_passed ? 'gate-passed' : 'gate-failed'}>{deepLearning.overall_passed ? 'Passed' : 'Failed'}</strong></li></ul></div>
        <div className="selection-conclusion"><strong>NOT SELECTED FOR LIVE INTEGRATION</strong><p>{deepLearning.conclusion}</p></div>
        <p className="selection-principle">Deep learning evaluated, not blindly deployed. ASTRA selects models based on measured mission-safety trade-offs rather than model complexity.</p>
        <small>Source: {deepLearning.source}</small>
      </section>
    </div>
  </details>
}

function App() {
  const [source, setSource] = useState('simulated')
  const [scenario, setScenario] = useState('normal')
  const [subsystemId, setSubsystemId] = useState('power')
  const [simulation, setSimulation] = useState(null)
  const [visibleCount, setVisibleCount] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(150)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [serviceStatus, setServiceStatus] = useState('connecting')
  const [healthCheckKey, setHealthCheckKey] = useState(0)
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [reviews, setReviews] = useState({})
  const [importFile, setImportFile] = useState(null)
  const [importResult, setImportResult] = useState(null)
  const [importError, setImportError] = useState('')
  const [timestampColumn, setTimestampColumn] = useState('timestamp')
  const [missionColumn, setMissionColumn] = useState('mission_id')
  const [mapping, setMapping] = useState({})
  const [unitsConfirmed, setUnitsConfirmed] = useState(false)
  const [importBusy, setImportBusy] = useState(false)
  const requestId = useRef(0)
  const simulationController = useRef(null)

  useEffect(() => {
    let active = true
    const controllers = new Set()
    const stopRequests = () => { controllers.forEach((controller) => controller.abort()); controllers.clear() }
    const checkHealth = async () => {
      if (!active) return
      const controller = new AbortController(); controllers.add(controller)
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`, { cache: 'no-store', signal: controller.signal })
        if (!active) return
        if (response.ok) {
          active = false; window.clearInterval(retryTimer); window.clearTimeout(startingTimer); window.clearTimeout(timeoutTimer); stopRequests(); setServiceStatus('ready'); return
        }
        setServiceStatus('starting')
      } catch (cause) { if (active && cause.name !== 'AbortError') setServiceStatus('starting') } finally { controllers.delete(controller) }
    }
    checkHealth()
    const startingTimer = window.setTimeout(() => { if (active) setServiceStatus('starting') }, HEALTH_RETRY_MS)
    const retryTimer = window.setInterval(checkHealth, HEALTH_RETRY_MS)
    const timeoutTimer = window.setTimeout(() => { if (!active) return; active = false; window.clearInterval(retryTimer); window.clearTimeout(startingTimer); stopRequests(); setServiceStatus('unavailable') }, HEALTH_TIMEOUT_MS)
    return () => { active = false; window.clearInterval(retryTimer); window.clearTimeout(startingTimer); window.clearTimeout(timeoutTimer); stopRequests() }
  }, [healthCheckKey])

  useEffect(() => () => simulationController.current?.abort(), [])

  useEffect(() => {
    if (!playing || !simulation) return undefined
    const timer = window.setInterval(() => setVisibleCount((count) => {
      if (count >= simulation.telemetry.length - 1) { setPlaying(false); return simulation.telemetry.length }
      const step = source === 'recorded' ? Math.max(1, Math.ceil(simulation.telemetry.length / TOTAL_POINTS)) : 1
      return Math.min(simulation.telemetry.length, count + step)
    }), speed)
    return () => window.clearInterval(timer)
  }, [playing, simulation, source, speed])

  const subsystem = SUBSYSTEMS.find((item) => item.id === subsystemId)
  const visible = useMemo(() => simulation?.telemetry.slice(0, visibleCount) ?? [], [simulation, visibleCount])
  const current = visible.at(-1)
  const prior = visible.at(-6)
  const allEvents = useMemo(() => simulation?.events ?? (simulation?.event ? [simulation.event] : []), [simulation])
  const visibleEvents = useMemo(() => allEvents.filter((event) => {
    const index = simulation?.telemetry.findIndex((point) => sameTimestamp(point.timestamp, event.alert_confirmed_time))
    return index >= 0 && visibleCount > index
  }), [allEvents, simulation, visibleCount])
  const selectedEvent = visibleEvents.find((event) => event.event_id === selectedEventId) ?? visibleEvents.at(-1) ?? null
  const activeAlert = Boolean(selectedEvent && current?.is_anomaly)
  const selectedScenario = SCENARIOS.find((item) => item.id === scenario)
  const visualisationOnly = source === 'recorded' && (simulation?.compatibility ?? importResult?.compatibility) === 'visualisation_only'
  const scoresUnavailable = source === 'recorded' && !simulation?.metrics
  const totalPoints = simulation?.telemetry.length ?? (source === 'simulated' ? TOTAL_POINTS : importResult?.import_metadata?.row_count ?? 0)
  const runComplete = Boolean(simulation && visibleCount >= simulation.telemetry.length)
  const faultStartTime = simulation?.metadata?.fault_start_timestamp ?? null
  const alertClass = activeAlert ? (selectedEvent.severity === 'high' ? 'state-critical' : 'state-warning') : 'state-normal'
  const selectedConfirmationIndex = selectedEvent ? simulation.telemetry.findIndex((point) => sameTimestamp(point.timestamp, selectedEvent.alert_confirmed_time)) : -1
  const alertJustConfirmed = selectedConfirmationIndex >= 0 && visibleCount === selectedConfirmationIndex + 1
  const alertHighlight = selectedConfirmationIndex >= 0 && visibleCount <= selectedConfirmationIndex + Math.max(1, Math.ceil(900 / speed))
  const workflowStage = !simulation || loading ? 0 : visibleEvents.length === 0 ? 1 : alertJustConfirmed ? 2 : 3
  const quality = derivedQuality(simulation)
  const eventEmptyMessage = visualisationOnly
    ? 'Detection is disabled for this visualisation-only import. No detector events or scores are generated.'
    : source === 'recorded'
      ? simulation ? 'No persistent event has been confirmed in the visible recorded replay.' : 'Validate and replay a compatible CSV to review detector evidence.'
      : emptyEventMessage({ hasSimulation: Boolean(simulation), scenario, runComplete })


  async function start() {
    if (serviceStatus !== 'ready' || loading || playing) return
    if (simulation && visibleCount < simulation.telemetry.length) { setPlaying(true); return }
    if (source === 'recorded') {
      const imported = recordedSimulation(importResult)
      if (!imported) { setError('Validate a recorded CSV before starting replay.'); return }
      setSimulation(imported); setVisibleCount(0); setSelectedEventId(imported.events[0]?.event_id ?? null); setReviews({}); setError(''); setPlaying(true)
      return
    }
    const id = ++requestId.current
    simulationController.current?.abort()
    const controller = new AbortController()
    simulationController.current = controller
    let didTimeout = false
    const timeout = window.setTimeout(() => { didTimeout = true; controller.abort() }, SIMULATION_TIMEOUT_MS)
    setLoading(true); setPlaying(false); setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scenario, points: TOTAL_POINTS, seed: SEED }), signal: controller.signal })
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(`API returned ${response.status}${detail ? `: ${detail.slice(0, 180)}` : ''}`)
      }
      let result
      try { result = await response.json() } catch { throw new Error('API returned an invalid JSON response') }
      if (id !== requestId.current) return
      setSimulation(result); setVisibleCount(0); setSelectedEventId((result.events ?? (result.event ? [result.event] : []))[0]?.event_id ?? null); setReviews({}); setPlaying(true)
    } catch (cause) {
      if (id !== requestId.current) return
      const detail = cause.name === 'AbortError' ? didTimeout ? 'The request exceeded the 45-second timeout.' : 'The request was cancelled.' : cause.message
      setError(`Unable to start simulation. ${detail}`)
    } finally {
      window.clearTimeout(timeout)
      if (simulationController.current === controller) simulationController.current = null
      if (id === requestId.current) setLoading(false)
    }
  }

  function reset(nextScenario = scenario) {
    requestId.current += 1; simulationController.current?.abort(); simulationController.current = null; setPlaying(false); setVisibleCount(0); setSimulation(null); setLoading(false); setImportBusy(false); setError(''); setScenario(nextScenario); setSelectedEventId(null); setReviews({})
  }

  function changeSource(nextSource) {
    const cleared = sourceResetState(nextSource)
    requestId.current += 1; simulationController.current?.abort(); simulationController.current = null
    setSource(cleared.source); setSimulation(cleared.simulation); setVisibleCount(cleared.visibleCount); setSelectedEventId(cleared.selectedEventId); setReviews(cleared.reviews); setError(cleared.error)
    setPlaying(false); setLoading(false); setImportBusy(false); setImportFile(cleared.importFile); setImportResult(cleared.importResult); setImportError(cleared.importError); setMapping({}); setTimestampColumn('timestamp'); setMissionColumn('mission_id'); setUnitsConfirmed(false); setSubsystemId('power')
  }

  async function requestImport(targetFile, options = {}) {
    const id = ++requestId.current
    simulationController.current?.abort()
    const controller = new AbortController()
    simulationController.current = controller
    const fileError = validateImportFile(targetFile)
    if (fileError) { setImportError(fileError); setImportResult(null); return }
    setImportBusy(true); setImportError(''); setSimulation(null); setPlaying(false); setVisibleCount(0); setSelectedEventId(null); setReviews({})
    const selectedTimestamp = options.timestampColumn ?? timestampColumn
    const selectedMission = options.missionColumn ?? missionColumn
    const selectedMapping = options.mapping ?? mapping
    const confirmedUnits = options.unitsConfirmed ?? unitsConfirmed
    try {
      const response = await fetch(`${API_BASE_URL}/api/import/telemetry`, {
        method: 'POST',
        headers: importHeaders({ file: targetFile, timestampColumn: selectedTimestamp, missionColumn: selectedMission, mapping: selectedMapping, unitsConfirmed: confirmedUnits }),
        body: targetFile,
        signal: controller.signal,
      })
      const payload = await response.json().catch(() => null)
      if (id !== requestId.current) return
      if (!response.ok) throw new Error(payload?.detail?.message ?? `Import API returned ${response.status}.`)
      setImportResult(payload)
      const nextTimestamp = payload.columns.includes(selectedTimestamp) ? selectedTimestamp : payload.columns[0]
      const nextMission = payload.columns.includes(selectedMission) ? selectedMission : ''
      setTimestampColumn(nextTimestamp); setMissionColumn(nextMission); setMapping(payload.mapping ?? {})
      if (payload.compatibility === 'invalid') setImportError(payload.validation?.errors?.join(' ') || 'The CSV is invalid.')
    } catch (cause) {
      if (id !== requestId.current) return
      setImportResult(null); setImportError(`Unable to validate CSV. ${cause.message}`)
    } finally { if (id === requestId.current) { setImportBusy(false); simulationController.current = null } }
  }

  function handleImportFile(nextFile) {
    reset(); setImportBusy(false)
    setImportFile(nextFile); setImportResult(null); setMapping({}); setTimestampColumn('timestamp'); setMissionColumn('mission_id'); setUnitsConfirmed(false)
    if (nextFile) requestImport(nextFile, { timestampColumn: 'timestamp', missionColumn: 'mission_id', mapping: {}, unitsConfirmed: false })
    else setImportError('')
  }

  async function loadDemoFile(filename) {
    const id = ++requestId.current
    try {
      const response = await fetch('/examples/' + filename)
      if (!response.ok) throw new Error('Demo file returned ' + response.status + '.')
      const content = await response.blob()
      if (id !== requestId.current) return
      handleImportFile(new File([content], filename, { type: 'text/csv' }))
    } catch (cause) {
      if (id !== requestId.current) return
      setImportError('Unable to load demonstration CSV. ' + cause.message)
    }
  }

  function selectEvent(event) {
    setSelectedEventId(event.event_id); setPlaying(false)
    const confirmationIndex = simulation.telemetry.findIndex((point) => sameTimestamp(point.timestamp, event.alert_confirmed_time))
    if (confirmationIndex >= 0) setVisibleCount(confirmationIndex + 1)
  }

  function updateReview(change) {
    if (!selectedEvent) return
    setReviews((currentReviews) => {
      if (change === null) { const next = { ...currentReviews }; delete next[selectedEvent.event_id]; return next }
      return { ...currentReviews, [selectedEvent.event_id]: { ...currentReviews[selectedEvent.event_id], ...change } }
    })
  }

  function exportEvent() {
    if (!selectedEvent) return
    const provenance = source === 'recorded' ? eventExportProvenance(importResult) : null
    const missionIdentifier = provenance ? importResult.import_metadata.mission_identifier : MISSION_ID
    const report = buildPrototypeEventReport({ event: selectedEvent, missionIdentifier, scenario: source === 'recorded' ? 'recorded_import' : scenario, review: reviews[selectedEvent.event_id], telemetrySource: simulation?.metadata?.source, provenance, dataQuality: quality })
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = eventFilename(selectedEvent); link.click(); URL.revokeObjectURL(url)
  }

  function printReport() {
    if (!selectedEvent) return
    const provenance = source === 'recorded' ? eventExportProvenance(importResult) : null
    const html = buildInvestigationReport({
      event: selectedEvent,
      missionIdentifier: provenance ? importResult.import_metadata.mission_identifier : MISSION_ID,
      source: simulation?.metadata?.source,
      sourceLabel: provenance?.sanitized_filename ?? selectedScenario.label,
      provenance,
      quality,
      review: reviews[selectedEvent.event_id],
    })
    const reportWindow = window.open('', '_blank')
    if (!reportWindow) { setError('The browser blocked the report window. Allow pop-ups and try again.'); return }
    reportWindow.document.open(); reportWindow.document.write(html); reportWindow.document.close(); reportWindow.focus(); reportWindow.print()
  }

  const serviceMessage = { connecting: 'Connecting to analysis service...', starting: 'Analysis service is starting. This may take up to one minute.', ready: 'Analysis service ready', unavailable: 'The analysis service is unavailable. It may be starting—retry in a few seconds.' }[serviceStatus]

  return <div className="app-shell"><header className="topbar"><div className="nav-brand"><strong>ASTRA</strong><span>Spacecraft Telemetry Decision Support</span></div><div className="nav-meta"><span>{source === 'simulated' ? 'Simulated Telemetry' : 'Recorded CSV Import'}</span><span>Mission {source === 'recorded' ? importResult?.import_metadata?.mission_identifier ?? 'Unassigned' : MISSION_ID}</span><span>Local Prototype</span></div></header><main>
    <section className="intro"><div className="intro-copy"><div className="kicker">Ground-based decision support / 01</div><h1>Mission telemetry,<br /><em>made understandable.</em></h1><p>ASTRA monitors compatible telemetry, detects persistent unusual behaviour and presents the evidence for operator review.</p><div className="boundary-labels"><span>Simulated and recorded telemetry prototype</span><span>Ground-based decision support</span><span>Human review required</span><span>No spacecraft command access</span></div></div><dl className="intro-facts"><div><dt>System status</dt><dd className={alertClass}>{visualisationOnly ? 'Visualisation only' : activeAlert ? `${selectedEvent.severity} alert` : 'Normal'}</dd></div><div><dt>Telemetry source</dt><dd>{source === 'simulated' ? selectedScenario.label : importResult?.import_metadata?.sanitized_filename ?? 'Recorded CSV'}</dd></div><div><dt>Current observation</dt><dd>{String(visibleCount).padStart(3, '0')} <span>/ {totalPoints}</span></dd></div></dl></section>
    <section className="demo-guide" aria-label="ASTRA replay guide"><p>ASTRA replays simulated scenarios or validated recorded CSV data. Detector conclusions are available only for the supported prototype profile.</p><ol><li><strong>1.</strong> Choose a source</li><li><strong>2.</strong> Validate and replay</li><li><strong>3.</strong> Review evidence</li></ol></section>
    <section className={`service-connection service-${serviceStatus}`} aria-live="polite"><span className="service-indicator" /><p>{serviceMessage}</p>{serviceStatus === 'unavailable' && <button type="button" onClick={() => { setServiceStatus('connecting'); setHealthCheckKey((key) => key + 1) }}>Retry</button>}</section>
    <section className="source-selector" aria-label="Telemetry source"><span>Telemetry source</span><div><button type="button" className={source === 'simulated' ? 'selected' : ''} aria-pressed={source === 'simulated'} onClick={() => changeSource('simulated')}>Simulated Scenario</button><button type="button" className={source === 'recorded' ? 'selected' : ''} aria-pressed={source === 'recorded'} onClick={() => changeSource('recorded')}>Recorded CSV Import</button></div><p>{source === 'simulated' ? 'Simulated telemetry demonstration' : 'Recorded telemetry import prototype'}</p></section>
    {source === 'recorded' && <ImportPanel file={importFile} result={importResult} error={importError} busy={importBusy} timestampColumn={timestampColumn} missionColumn={missionColumn} mapping={mapping} unitsConfirmed={unitsConfirmed} onFile={handleImportFile} onDemo={loadDemoFile} onTimestamp={(value) => { reset(); setTimestampColumn(value); setImportResult((result) => ({ ...result, compatibility: 'invalid', compatibility_label: 'Revalidate mapping' })) }} onMission={(value) => { reset(); setMissionColumn(value); setImportResult((result) => ({ ...result, compatibility: 'invalid', compatibility_label: 'Revalidate mapping' })) }} onMapping={(column, target) => { reset(); setMapping((currentMapping) => ({ ...currentMapping, [column]: target })); setImportResult((result) => ({ ...result, compatibility: 'invalid', compatibility_label: 'Revalidate mapping' })) }} onUnits={(value) => { reset(); setUnitsConfirmed(value); setImportResult((result) => ({ ...result, compatibility: 'invalid', compatibility_label: 'Revalidate mapping' })) }} onValidate={() => requestImport(importFile)} />}
    <section className="live-workflow"><span className="workflow-label">{source === 'simulated' ? 'Simulated replay workflow' : 'Recorded telemetry workflow'}</span><div>{WORKFLOW_STAGES.map((stage, index) => <span key={stage} className={workflowStage === index ? 'active' : ''}>{stage}{index < 3 && <i>→</i>}</span>)}</div></section>
    <section className="control-bar" aria-busy={loading || importBusy}><div className="scenario-block">{source === 'simulated' ? <><div className="scenario-control" role="group" aria-label="Simulation scenario">{SCENARIOS.map((item) => <button key={item.id} type="button" className={scenario === item.id ? 'selected' : ''} onClick={() => reset(item.id)} aria-pressed={scenario === item.id}>{item.label}</button>)}</div><p>{selectedScenario.description}</p></> : <p>{importResult?.compatibility === 'compatible' ? 'Uploaded recorded telemetry is compatible with astra-sim-v1.' : importResult?.compatibility === 'visualisation_only' ? 'Replay is available without detector, risk or health conclusions.' : 'Upload and validate a CSV before replay.'}</p>}</div><div className="action-control"><button type="button" className="start-button" onClick={start} disabled={serviceStatus !== 'ready' || loading || importBusy || playing || (source === 'recorded' && (!importResult || importResult.compatibility === 'invalid'))} title={serviceStatus !== 'ready' ? 'Start is available when the analysis service is ready' : source === 'recorded' && !importResult ? 'Validate a CSV before replay' : undefined}><CirclePlay size={16} />{loading ? 'Loading…' : simulation && visibleCount < simulation.telemetry.length ? 'Resume' : 'Start Replay'}</button><button type="button" onClick={() => setPlaying(false)} disabled={!playing}><CirclePause size={16} />Pause</button><button type="button" onClick={() => reset()}><RotateCcw size={15} />Reset</button></div><label className="speed-control">Playback speed <select value={speed} disabled={loading || importBusy} aria-label="Playback speed" onChange={(changeEvent) => setSpeed(Number(changeEvent.target.value))}>{SPEEDS.map((item) => <option key={item.ms} value={item.ms}>{item.label}</option>)}</select></label></section>
    {error && <div className="error-message" role="alert">{error}</div>}
    <section className="status-strip"><div className="status-item"><span>Telemetry Status</span><strong className={visualisationOnly ? 'state-warning' : alertClass}>{visualisationOnly ? 'VISUAL ONLY' : activeAlert ? selectedEvent.severity.toUpperCase() : 'NORMAL'}</strong><small>{visualisationOnly ? 'Detection disabled for this dataset' : activeAlert ? 'Persistent pattern detected' : 'No active alert'}</small></div><div className="status-item"><span>Health Score</span><strong>{scoresUnavailable ? '—' : (current?.health_score ?? 100).toFixed(1)}{!scoresUnavailable && <i>/100</i>}</strong><small>{scoresUnavailable ? 'Awaiting compatible replay' : 'Prototype heuristic indicator'}</small></div><div className="status-item"><span>Risk Score</span><strong>{scoresUnavailable ? '—' : (current?.risk_score ?? 0).toFixed(1)}{!scoresUnavailable && <i>/100</i>}</strong><small>{scoresUnavailable ? 'Awaiting compatible replay' : 'Prototype heuristic indicator'}</small></div><div className="status-item"><span>Active Alerts</span><strong>{visualisationOnly ? '—' : String(visibleEvents.filter((event) => event.status === 'active').length).padStart(2, '0')}</strong><small>{visualisationOnly ? 'Detector not run' : visibleEvents.length ? 'Human review required' : 'No persistent alert'}</small></div><div className="status-item analysis-time"><span>Run Analysis Time</span><strong>{runAnalysisTime(simulation?.metrics?.processing_latency_ms)}</strong><small>{timePerObservation(simulation?.metrics?.processing_latency_ms, simulation?.telemetry.length)}</small><small>Backend model execution; excludes spacecraft transmission time.</small></div></section>
    <div className="monitor-grid"><section className="telemetry-area"><div className="section-heading"><div><span className="kicker">{source === 'simulated' ? 'Simulated telemetry demonstration / 02' : 'Recorded telemetry import prototype / 02'}</span><h2>Telemetry</h2></div><span className="section-count">{visibleCount} of {totalPoints} observations</span></div>{visualisationOnly ? <><div className="chart-head"><div><span className="normalized-label">Visualisation-only normalized view</span><h3>Uploaded channels</h3><p>Up to three uploaded numeric series are independently scaled from their observed minimum to maximum for visual comparison. Tooltips preserve the uploaded numeric values; physical units are unknown.</p></div><span className="chart-time">{timeLabel(current?.timestamp)}</span></div><div className="chart-legend">{(simulation?.visualization_channels ?? []).slice(0, 3).map((key, index) => <span key={key}><i className={`line-swatch line-${index}`} />{key}</span>)}</div><ImportedTelemetryChart data={visible} channels={simulation?.visualization_channels ?? importResult?.visualization_channels ?? []} /><p className="detection-disabled">Detection disabled because this dataset does not match a validated ASTRA prototype profile.</p></> : <><div className="subsystem-tabs">{SUBSYSTEMS.map((item) => <button key={item.id} type="button" aria-pressed={subsystemId === item.id} className={subsystemId === item.id ? 'active' : ''} onClick={() => setSubsystemId(item.id)}>{item.label}</button>)}</div><div className="chart-head"><div><span className="normalized-label">Normalized comparison view</span><h3>{subsystem.label}</h3><p>Signals are centred on the midpoint of their listed display range and divided by half that range. −1 and +1 are the listed lower and upper display references. Raw values and units remain in tooltips and the table.</p></div><span className="chart-time">{timeLabel(current?.timestamp)}</span></div><div className="chart-legend">{subsystem.keys.map((key, index) => <span key={key}><i className={`line-swatch line-${index}`} />{CHANNELS[key].label}</span>)}</div><TelemetryChart data={visible} subsystem={subsystem} event={selectedEvent} faultStartTime={faultStartTime} /><div className="table-heading"><h3>Latest values</h3><span>Selected-event attribution</span></div><div className="table-scroll"><table><thead><tr><th>Channel</th><th>Latest value</th><th>Display range</th><th>Trend</th><th>Detector state</th></tr></thead><tbody>{subsystem.keys.map((key) => { const contributes = selectedEvent?.contributing_channels.includes(key); const value = current?.[key]; const within = value != null && value >= CHANNELS[key].low && value <= CHANNELS[key].high; return <tr key={key} className={contributes ? `contributing-row severity-${selectedEvent.severity}` : ''}><td>{CHANNELS[key].label}</td><td className="mono-value">{reading(key, value)}</td><td className="mono-value">{CHANNELS[key].low}–{CHANNELS[key].high} {CHANNELS[key].unit}</td><td>{trend(key, value, prior?.[key])}</td><td className={contributes ? selectedEvent.severity === 'high' ? 'state-critical' : 'state-warning' : 'muted-cell'}>{contributes ? 'Contributing to event' : value == null ? 'Awaiting telemetry' : within ? 'Within expected range' : 'Outside display range'}</td></tr> })}</tbody></table></div></>}</section><aside className="event-area event-review"><span className="kicker">Operator workflow / 03</span><h2>Event timeline</h2><EventList events={visibleEvents} selectedId={selectedEvent?.event_id} reviews={reviews} onSelect={selectEvent} /><h2 className="review-title">Event review</h2><EventReview event={selectedEvent} faultStartTime={faultStartTime} review={selectedEvent ? reviews[selectedEvent.event_id] : null} onReviewChange={updateReview} onExport={exportEvent} onReport={printReport} justConfirmed={alertHighlight} emptyMessage={eventEmptyMessage} /></aside></div>
    <DataQuality quality={quality} />
    {runComplete && <section className="run-summary"><div className="run-summary-heading"><div><span className="kicker">Replay complete</span><h2>End-of-run summary</h2></div>{visualisationOnly ? <p>Visualisation complete; detector conclusions unavailable.</p> : allEvents.length === 0 && <p>No persistent event detected.</p>}</div><dl><div><dt>Observations replayed</dt><dd>{simulation.telemetry.length}</dd></div><div><dt>Persistent events</dt><dd>{visualisationOnly ? 'Not evaluated' : allEvents.length}</dd></div><div><dt>Contributing channels</dt><dd>{visualisationOnly ? 'Not evaluated' : new Set(allEvents.flatMap((event) => event.contributing_channels)).size}</dd></div><div><dt>Average analysis time</dt><dd>{visualisationOnly ? 'Not run' : timePerObservation(simulation.metrics?.processing_latency_ms, simulation.telemetry.length)}</dd></div><div><dt>Operator review requested</dt><dd>{visualisationOnly ? 'No detector decision' : allEvents.length ? 'Yes' : 'No'}</dd></div></dl></section>}
    <section className="method-section"><div className="method-intro"><span className="kicker">Detector and source status / 04</span><h2>What is running</h2><p>The live prototype, recorded import contract and offline research use separate configurations and evidence. Planned mission integration remains future work.</p></div><div className="method-columns"><div><h3>Live prototype</h3><p>React, Vite and Recharts interface; FastAPI and Uvicorn backend; fixed operating thresholds and scikit-learn Isolation Forest; trend corroboration; persistence; simulated telemetry and compatible recorded CSV replay.</p></div><div><h3>Offline research evaluation</h3><p>Public NASA SMAP/MSL telemetry from Telemanom; robust threshold, Isolation Forest, combined detector and PyTorch LSTM Autoencoder; frozen evaluation protocols.</p></div><div><h3>Planned mission integration</h3><p>No live spacecraft link is implemented. Arbitrary uploaded telemetry is not detector compatible. Mission-specific integration and qualification remain future work.</p></div></div></section>
    <ValidationEvidence />
    <footer className="boundary"><span>System boundary</span><p>ASTRA begins after telemetry has been received and decoded by the ground system. Human review is required. This prototype does not communicate with or control a spacecraft.</p></footer>
  </main></div>
}

export default App
