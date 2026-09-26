import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const evidence = JSON.parse(readFileSync(new URL('./validationEvidence.json', import.meta.url), 'utf8'))
const appSource = readFileSync(new URL('./App.jsx', import.meta.url), 'utf8')

test('validation evidence visibly separates the two frozen evaluations', () => {
  assert.equal(evidence.phase1c.label, 'Phase 1C — Public Baseline Evaluation')
  assert.equal(evidence.phase4.label, 'Phase 4 — Deep Learning Experiment')
  assert.match(evidence.holdout_notice, /different frozen holdouts/)
})

test('Phase 4 records the failed gate and non-live experimental status', () => {
  assert.equal(evidence.phase4.overall_passed, false)
  assert.match(evidence.phase4.experiment.status, /^Experimental; not used by the live prototype$/)
  assert.equal(evidence.phase4.gates.find((gate) => gate.key === 'macro_f1_gain').passed, false)
  assert.equal(evidence.phase4.gates.find((gate) => gate.key === 'event_recall_not_lower').passed, false)
})

test('LSTM is evidence only and is absent from live controls', () => {
  const scenarioBlock = appSource.match(/const SCENARIOS = \[([\s\S]*?)\n\]/)?.[1] ?? ''
  const controlBlock = appSource.match(/<section className="control-bar"([\s\S]*?)<\/section>/)?.[1] ?? ''
  const liveStack = appSource.match(/<h3>Live prototype<\/h3><p>(.*?)<\/p>/)?.[1] ?? ''
  assert.doesNotMatch(scenarioBlock, /lstm/i)
  assert.doesNotMatch(controlBlock, /lstm/i)
  assert.doesNotMatch(liveStack, /pytorch|lstm/i)
  assert.match(appSource, /NOT SELECTED FOR LIVE INTEGRATION/)
})
