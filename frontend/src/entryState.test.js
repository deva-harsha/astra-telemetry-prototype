import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'
import { ENTRY_SESSION_KEY, entryTransitionMs, focusAfterEntry, initialEntryPhase, showImportMapping } from './entryState.js'

let server
let EntryScreen
let App

before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  EntryScreen = (await server.ssrLoadModule('/src/EntryScreen.jsx')).default
  App = (await server.ssrLoadModule('/src/App.jsx')).default
})
after(async () => { await server?.close() })

function findButtons(node, found = []) {
  if (!node || typeof node !== 'object') return found
  if (Array.isArray(node)) { node.forEach((child) => findButtons(child, found)); return found }
  if (node.type === 'button') found.push(node)
  findButtons(node.props?.children, found)
  return found
}

test('entry renders mission copy, actions, genuine service status and boundaries', () => {
  const html = renderToStaticMarkup(createElement(EntryScreen, {
    phase: 'visible', serviceMessage: 'Analysis service ready', serviceStatus: 'ready',
    onEnter: () => {}, onExplore: () => {}, headingRef: null,
  }))
  for (const phrase of ['Spacecraft Telemetry Decision Support', 'GROUND-BASED MISSION INTELLIGENCE', 'See the signal.', 'Understand the event.', 'ENTER MISSION CONTROL', 'EXPLORE CAPABILITIES', 'Simulated and recorded telemetry', 'Hybrid anomaly detection', 'Human review required', 'No spacecraft command access', 'Analysis service ready', 'MISSION: ASTRA-01', 'PROTOTYPE ENVIRONMENT']) assert.ok(html.includes(phrase), phrase)
  assert.ok(!html.includes('password'))
  assert.ok(html.includes('aria-hidden="true"'))
})

test('entry actions invoke the respective console navigation callbacks', () => {
  const calls = []
  const tree = EntryScreen({ phase: 'visible', serviceMessage: 'Connecting', serviceStatus: 'connecting', onEnter: () => calls.push('enter'), onExplore: () => calls.push('explore'), headingRef: null })
  const buttons = findButtons(tree)
  assert.equal(buttons.length, 2)
  buttons[0].props.onClick()
  buttons[1].props.onClick()
  assert.deepEqual(calls, ['enter', 'explore'])
})

test('session entry preference is temporary and tolerates blocked storage', () => {
  assert.equal(initialEntryPhase(null), 'visible')
  assert.equal(initialEntryPhase({ getItem: () => '1' }), 'hidden')
  assert.equal(initialEntryPhase({ getItem: () => null }), 'visible')
  assert.equal(initialEntryPhase({ getItem: () => { throw Error('blocked') } }), 'visible')
  assert.equal(ENTRY_SESSION_KEY, 'astra-mission-control-entered')
})

test('reduced motion removes the entry delay and focus transfers to the correct target', () => {
  assert.equal(entryTransitionMs(true), 0)
  assert.ok(entryTransitionMs(false) >= 300 && entryTransitionMs(false) <= 600)
  const calls = []
  const consoleHeading = { focus: () => calls.push('console') }
  const capabilities = { open: false, querySelector: () => ({ focus: () => calls.push('capabilities') }), scrollIntoView: () => calls.push('scroll') }
  assert.equal(focusAfterEntry({ explore: false, consoleHeading, capabilities }), 'console')
  assert.equal(focusAfterEntry({ explore: true, consoleHeading, capabilities }), 'capabilities')
  assert.deepEqual(calls, ['console', 'capabilities', 'scroll'])
  assert.equal(capabilities.open, true)
})

test('CSV mapping stays available before and after invalid validation, then collapses until edited', () => {
  assert.equal(showImportMapping({ expanded: false, validationRequested: false, compatibility: 'visualisation_only' }), true)
  assert.equal(showImportMapping({ expanded: false, validationRequested: true, compatibility: 'invalid' }), true)
  assert.equal(showImportMapping({ expanded: false, validationRequested: true, compatibility: undefined }), true)
  assert.equal(showImportMapping({ expanded: false, validationRequested: true, compatibility: 'compatible' }), false)
  assert.equal(showImportMapping({ expanded: false, validationRequested: true, compatibility: 'visualisation_only' }), false)
  assert.equal(showImportMapping({ expanded: true, validationRequested: true, compatibility: 'compatible' }), true)
})

test('console markup preserves accessible controls and one disclosed method section', () => {
  const priorWindow = globalThis.window
  globalThis.window = { sessionStorage: { getItem: () => '1' } }
  try {
    const html = renderToStaticMarkup(createElement(App))
    assert.ok(html.includes('Skip to mission control'))
    assert.ok(html.includes('id="console-heading"'))
    for (const phrase of ['Simulated Scenario', 'Recorded CSV Import', 'Normal Operation', 'Thermal Fault', 'Power Fault', 'Start Replay', 'Pause', 'Reset', 'Playback speed', 'Detector Comparison Lab', 'Validation evidence', 'Launch screen']) assert.ok(html.includes(phrase), phrase)
    assert.equal((html.match(/What is running/g) ?? []).length, 1)
    assert.ok(html.includes('id="capabilities"'))
    assert.ok(html.includes('<details'))
  } finally { globalThis.window = priorWindow }
})
