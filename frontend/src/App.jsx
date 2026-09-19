import { useEffect, useMemo, useRef, useState } from 'react'
import { CirclePause, CirclePlay, RotateCcw } from 'lucide-react'
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const TOTAL_POINTS = 180
const SEED = 42

const SCENARIOS = [
  { id: 'normal', label: 'Normal Operation', description: 'Control run containing no injected fault.' },
  { id: 'thermal_fault', label: 'Thermal Fault', description: 'Simulates gradual abnormal heating across related subsystems.' },
  { id: 'power_fault', label: 'Power Fault', description: 'Simulates unusual voltage and current behaviour.' },
]

// Display references based on the simulator's normal operating values. They do
// not replace the backend's threshold or model decisions.
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

const STEPS = [
  ['01', 'Simulate', 'Generate repeatable multi-subsystem telemetry.'],
  ['02', 'Learn', 'Isolation Forest learns the initial normal operating segment.'],
  ['03', 'Detect', 'Threshold rules, Isolation Forest and persistence identify unusual behaviour.'],
  ['04', 'Explain', 'ASTRA presents affected signals, timing, severity and evidence for operator review.'],
]

const METHOD = [
  ['Data source', 'Controlled simulated spacecraft telemetry'],
  ['Model', 'Threshold baseline + Isolation Forest'],
  ['Training', 'Initial normal portion of each simulation run'],
  ['Confirmation rule', 'Three consecutive unusual observations'],
  ['Scores', 'Prototype heuristic indicators, not failure probabilities'],
  ['Planned validation', 'Public anonymised NASA/JPL SMAP and MSL telemetry'],
]

const LINE_COLORS = ['#f4f3ee', '#a3a3a3', '#737373']
const LINE_DASHES = [undefined, '6 4', '2 4']

function timeLabel(value) {
  if (!value) return '—'
  return new Date(value).toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', timeZone: 'UTC',
  }) + ' UTC'
}

function reading(key, value) {
  if (value == null) return '—'
  const digits = key === 'radiation_level' ? 3 : key === 'attitude_error' ? 2 : 1
  return `${Number(value).toFixed(digits)} ${CHANNELS[key].unit}`
}

function runAnalysisTime(milliseconds) {
  if (milliseconds == null) return '—'
  return milliseconds >= 1000
    ? `${(milliseconds / 1000).toFixed(2)} s/run`
    : `${milliseconds.toFixed(1)} ms/run`
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

function TelemetryChart({ data, subsystem, scenario, totalPoints, event, eventSeen }) {
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

  const faultIndex = Math.floor(totalPoints * 0.6)
  const faultTime = scenario !== 'normal' && data.length > faultIndex ? data[faultIndex]?.timestamp : null
  const eventTime = eventSeen ? event?.event_start_time : null
  const eventStartIndex = eventTime ? data.findIndex((point) => point.timestamp === eventTime) : -1
  const detectionTime = eventStartIndex >= 0 ? data[eventStartIndex + 2]?.timestamp : null
  const eventEndIndex = eventStartIndex >= 0 ? Math.min(data.length - 1, eventStartIndex + event.duration - 1) : -1
  const eventEndTime = eventEndIndex >= 0 ? data[eventEndIndex]?.timestamp : null

  return <div className="chart-frame">
    {data.length === 0 ? <div className="chart-empty"><span>Telemetry plot ready</span><p>Start a simulation to reveal the 180-observation mission replay.</p></div> :
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 24, right: 18, left: 0, bottom: 6 }}>
          <CartesianGrid stroke="#292929" strokeDasharray="2 5" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={timeLabel} minTickGap={50} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={{ stroke: '#343434' }} tickLine={false} />
          <YAxis domain={['auto', 'auto']} tick={{ fill: '#858585', fontSize: 11, fontFamily: 'Consolas, monospace' }} axisLine={false} tickLine={false} width={38} />
          <Tooltip labelFormatter={timeLabel} formatter={(value, name, item) => [reading(item.dataKey, item.payload[`raw_${item.dataKey}`]), name]} contentStyle={{ background: '#171717', border: '1px solid #3a3a3a', borderRadius: 2, color: '#f4f3ee', fontSize: 12 }} labelStyle={{ color: '#a3a3a3', marginBottom: 8 }} />
          {eventTime && eventEndTime && <ReferenceArea x1={eventTime} x2={eventEndTime} fill={event?.severity === 'high' ? '#a9534c' : '#b48b50'} fillOpacity={0.12} strokeOpacity={0} />}
          {faultTime && <ReferenceLine x={faultTime} stroke="#b48b50" strokeDasharray="4 4" label={{ value: 'Fault injected', position: 'insideTopRight', fill: '#c7a677', fontSize: 10 }} />}
          {detectionTime && <ReferenceLine x={detectionTime} stroke="#b66d62" strokeDasharray="2 3" label={{ value: 'Alert confirmed', position: 'insideTopLeft', fill: '#d19489', fontSize: 10 }} />}
          {subsystem.keys.map((key, index) => <Line key={key} type="monotone" dataKey={key} name={CHANNELS[key].label} stroke={LINE_COLORS[index]} strokeWidth={index === 0 ? 2 : 1.6} strokeDasharray={LINE_DASHES[index]} dot={false} activeDot={{ r: 3 }} isAnimationActive={false} />)}
        </LineChart>
      </ResponsiveContainer>}
  </div>
}

function App() {
  const [scenario, setScenario] = useState('normal')
  const [subsystemId, setSubsystemId] = useState('power')
  const [simulation, setSimulation] = useState(null)
  const [visibleCount, setVisibleCount] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(150)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const requestId = useRef(0)

  useEffect(() => {
    if (!playing || !simulation) return undefined
    const timer = window.setInterval(() => setVisibleCount((count) => {
      if (count >= simulation.telemetry.length - 1) {
        setPlaying(false)
        return simulation.telemetry.length
      }
      return count + 1
    }), speed)
    return () => window.clearInterval(timer)
  }, [playing, simulation, speed])

  const subsystem = SUBSYSTEMS.find((item) => item.id === subsystemId)
  const visible = useMemo(() => simulation?.telemetry.slice(0, visibleCount) ?? [], [simulation, visibleCount])
  const current = visible.at(-1)
  const prior = visible.at(-6)
  const event = simulation?.event
  const eventIndex = event ? simulation.telemetry.findIndex((point) => point.timestamp === event.event_start_time) : -1
  const eventSeen = eventIndex >= 0 && visibleCount >= eventIndex + 3
  const activeAlert = eventSeen && Boolean(current?.is_anomaly)
  const alertClass = activeAlert ? (current?.severity === 'high' ? 'state-critical' : 'state-warning') : 'state-normal'
  const displayedSeverity = activeAlert ? current?.severity : event?.severity
  const selectedScenario = SCENARIOS.find((item) => item.id === scenario)

  async function start() {
    if (simulation && visibleCount < simulation.telemetry.length) {
      setPlaying(true)
      return
    }
    const id = ++requestId.current
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/simulate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario, points: TOTAL_POINTS, seed: SEED }),
      })
      if (!response.ok) throw new Error(`API returned ${response.status}`)
      const result = await response.json()
      if (id !== requestId.current) return
      setSimulation(result)
      setVisibleCount(0)
      setPlaying(true)
    } catch (cause) {
      if (id === requestId.current) setError(`Unable to start simulation. Check that the API is available at ${API_BASE_URL}. ${cause.message}`)
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }

  function reset(nextScenario = scenario) {
    requestId.current += 1
    setPlaying(false)
    setVisibleCount(0)
    setSimulation(null)
    setLoading(false)
    setError('')
    setScenario(nextScenario)
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="nav-brand"><strong>ASTRA</strong><span>Spacecraft Telemetry Decision Support</span></div>
      <div className="nav-meta"><span>Simulated Telemetry</span><span>Mission ASTRA-01</span><span>Local Prototype</span></div>
    </header>

    <main>
      <section className="intro">
        <div className="intro-copy"><div className="kicker">Ground-based decision support / 01</div><h1>Mission telemetry,<br /><em>made understandable.</em></h1><p>ASTRA monitors multi-subsystem telemetry, detects persistent unusual behaviour and presents the evidence for operator review.</p></div>
        <dl className="intro-facts"><div><dt>System status</dt><dd className={alertClass}>{activeAlert ? `${current?.severity} alert` : 'Normal'}</dd></div><div><dt>Selected scenario</dt><dd>{selectedScenario.label}</dd></div><div><dt>Current observation</dt><dd>{String(visibleCount).padStart(3, '0')} <span>/ {TOTAL_POINTS}</span></dd></div></dl>
      </section>

      <section className="demo-guide" aria-label="Demonstration flow">
        <p>Telemetry received <span>→</span> ASTRA studies related signals <span>→</span> Persistent anomaly detected <span>→</span> Operator gets an explained alert</p>
        <small>Select a scenario → Start simulation → Review the detected event</small>
      </section>

      <section className="control-bar" aria-label="Simulation controls">
        <div className="scenario-block"><div className="scenario-control" role="group" aria-label="Scenario">{SCENARIOS.map((item) => <button key={item.id} type="button" className={scenario === item.id ? 'selected' : ''} aria-pressed={scenario === item.id} onClick={() => reset(item.id)}>{item.label}</button>)}</div><p>{selectedScenario.description}</p></div>
        <div className="action-control"><button type="button" className="start-button" onClick={start} disabled={loading || playing}><CirclePlay size={16} />{loading ? 'Loading…' : 'Start Simulation'}</button><button type="button" onClick={() => setPlaying(false)} disabled={!playing}><CirclePause size={16} />Pause</button><button type="button" onClick={() => reset()}><RotateCcw size={15} />Reset</button></div>
        <label className="speed-control">Playback speed <select value={speed} onChange={(eventValue) => setSpeed(Number(eventValue.target.value))}>{SPEEDS.map((item) => <option key={item.ms} value={item.ms}>{item.label}</option>)}</select></label>
      </section>
      {error && <div className="error-message" role="alert">{error}</div>}

      <section className="status-strip" aria-label="Current mission status">
        <div className="status-item"><span>Spacecraft Status</span><strong className={alertClass}>{activeAlert ? current?.severity?.toUpperCase() : 'NORMAL'}</strong><small>{activeAlert ? 'Persistent pattern detected' : 'No active alert'}</small></div>
        <div className="status-item"><span>Health Score</span><strong>{(current?.health_score ?? 100).toFixed(1)}<i>/100</i></strong><small>Prototype heuristic indicator</small></div>
        <div className="status-item"><span>Risk Score</span><strong>{(current?.risk_score ?? 0).toFixed(1)}<i>/100</i></strong><small>Prototype heuristic indicator</small></div>
        <div className="status-item"><span>Active Alerts</span><strong>{activeAlert ? '01' : '00'}</strong><small>{activeAlert ? 'Operator review requested' : 'No persistent alert'}</small></div>
        <div className="status-item analysis-time"><span>Run Analysis Time</span><strong>{runAnalysisTime(simulation?.metrics.processing_latency_ms)}</strong><small>{timePerObservation(simulation?.metrics.processing_latency_ms, simulation?.telemetry.length)}</small><small>Backend model execution; excludes spacecraft transmission time.</small></div>
      </section>

      <div className="monitor-grid">
        <section className="telemetry-area" aria-labelledby="telemetry-title">
          <div className="section-heading"><div><span className="kicker">Live replay / 02</span><h2 id="telemetry-title">Telemetry</h2></div><span className="section-count">{visibleCount} of {TOTAL_POINTS} observations</span></div>
          <div className="subsystem-tabs" role="tablist" aria-label="Telemetry subsystem">{SUBSYSTEMS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={subsystemId === item.id} className={subsystemId === item.id ? 'active' : ''} onClick={() => setSubsystemId(item.id)}>{item.label}</button>)}</div>
          <div className="chart-head"><div><span className="normalized-label">Normalized comparison view</span><h3>{subsystem.label}</h3><p>Signals with different physical units are scaled for visual comparison. Each line is centred on the midpoint of its listed normal display range; −1 and +1 represent that range’s lower and upper bounds. Raw values and units remain in the table and tooltip.</p></div><span className="chart-time">{timeLabel(current?.timestamp)}</span></div>
          <div className="chart-legend">{subsystem.keys.map((key, index) => <span key={key}><i className={`line-swatch line-${index}`} />{CHANNELS[key].label}</span>)}</div>
          <TelemetryChart data={visible} subsystem={subsystem} scenario={scenario} totalPoints={TOTAL_POINTS} event={event} eventSeen={eventSeen} />
          <div className="table-heading"><h3>Latest values</h3><span>Observation-wide detector state</span></div>
          <div className="table-scroll"><table><thead><tr><th>Channel</th><th>Latest value</th><th>Normal range</th><th>Trend</th><th>Detector state</th></tr></thead><tbody>{subsystem.keys.map((key) => { const contributes = eventSeen && event.contributing_channels.includes(key); return <tr key={key}><td>{CHANNELS[key].label}</td><td className="mono-value">{reading(key, current?.[key])}</td><td className="mono-value">{CHANNELS[key].low}–{CHANNELS[key].high} {CHANNELS[key].unit}</td><td>{trend(key, current?.[key], prior?.[key])}</td><td className={contributes ? 'state-warning' : 'muted-cell'}>{contributes ? 'Contributing to event' : 'Within expected range'}</td></tr> })}</tbody></table></div>
        </section>

        <aside className="event-area" aria-labelledby="event-title"><span className="kicker">Operator review / 03</span><h2 id="event-title">Event review</h2>{eventSeen ? <div className="event-content"><div className="event-state"><span className={`severity-label severity-${displayedSeverity}`}>{displayedSeverity} severity</span><span>{activeAlert ? 'Active' : 'Observed'}</span></div><section className="review-section detection-summary"><h4>What ASTRA detected</h4><h3>{event.title}</h3><dl className="event-fields"><div><dt>Affected subsystem</dt><dd>{event.affected_subsystem}</dd></div><div><dt>Event start</dt><dd>{timeLabel(event.event_start_time)}</dd></div><div><dt>Duration</dt><dd>{Math.min(event.duration, visibleCount - eventIndex)} min</dd></div><div><dt>Contributing channels</dt><dd>{event.contributing_channels.map((key) => CHANNELS[key]?.label ?? key).join(', ')}</dd></div></dl></section><section className="review-section"><h4>Why it generated an alert</h4><p>{event.explanation}</p></section><section className="review-section"><h4>Operator action</h4><p>{event.operator_review_message}</p></section></div> : <div className="empty-event"><div className="empty-rule" /><h3>No active alert</h3><p>No persistent unusual telemetry pattern detected.</p><small>{simulation ? 'The replay continues to assess incoming observations.' : 'Select a scenario and start the simulation to begin review.'}</small></div>}</aside>
      </div>

      <section className="method-section" aria-labelledby="method-title"><div className="method-intro"><span className="kicker">Data and method / 04</span><h2 id="method-title">How this prototype works</h2><p>A repeatable local demonstration of anomaly detection and operator-facing evidence.</p></div><div className="steps">{STEPS.map(([number, title, description]) => <div className="step" key={number}><span>{number}</span><h3>{title}</h3><p>{description}</p></div>)}</div><dl className="method-facts">{METHOD.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
      <footer className="boundary"><span>System boundary</span><p>ASTRA begins after telemetry has been received and decoded by the ground system. This prototype does not communicate with or control a spacecraft.</p></footer>
    </main>
  </div>
}

export default App
