import assert from 'node:assert/strict'
import test from 'node:test'

import { detectorComparison, pipelineStages, syntheticComparison } from './detectorUtils.js'

function point(index, { threshold = false, isolation = false, trend = false, streak = 0, confirmed = false, fault = false } = {}) {
  return {
    timestamp: `2026-01-01T00:0${index}:00Z`, fault_active: fault,
    detector_reasoning: {
      threshold: { state: threshold ? 'candidate' : 'normal', confirmed_by_persistence: threshold && confirmed, channels: threshold ? ['battery_voltage'] : [] },
      isolation_forest: { unusual: isolation, confirmed_by_persistence: isolation && confirmed },
      trend: { corroborated: trend, signals: trend ? [{ channel: 'battery_current', direction: 'rising' }] : [] },
      persistence: { current_count: streak, confirmed },
      final_decision: { candidate: threshold || (isolation && trend), confirmed },
    },
  }
}

test('pipeline never confirms before genuine final confirmation', () => {
  assert.deepEqual(pipelineStages(), ['Waiting', 'Waiting', 'Waiting', 'Waiting', 'Waiting'])
  assert.deepEqual(pipelineStages(point(0, { threshold: true, streak: 1 })), ['Candidate', 'Normal', 'Normal', 'Candidate', 'Normal'])
  assert.deepEqual(pipelineStages(point(2, { threshold: true, streak: 3, confirmed: true })), ['Candidate', 'Normal', 'Normal', 'Confirmed', 'Confirmed'])
  assert.ok(pipelineStages(point(1, { isolation: true, trend: true, streak: 2 })).every((state) => state !== 'Confirmed'))
})

test('comparison derives method candidates without changing source points', () => {
  const points = [point(0), point(1, { isolation: true }), point(2, { isolation: true, trend: true, streak: 1 }), point(3, { threshold: true, streak: 2 }), point(4, { threshold: true, streak: 3, confirmed: true })]
  const before = structuredClone(points)
  const comparison = detectorComparison(points)
  assert.equal(comparison.methods.find((item) => item.id === 'threshold').candidateObservations, 2)
  assert.equal(comparison.methods.find((item) => item.id === 'isolation').candidateObservations, 2)
  assert.equal(comparison.methods.find((item) => item.id === 'hybrid').confirmedEventCount, 1)
  assert.ok(comparison.agreement.disagree > 0)
  assert.deepEqual(points, before)
})

test('synthetic comparison uses supplied labels and does not calculate accuracy', () => {
  const result = syntheticComparison([point(0), point(1, { fault: true }), point(2, { threshold: true, streak: 1, fault: true }), point(3, { threshold: true, streak: 3, confirmed: true, fault: true })])
  assert.equal(result.faultStart.index, 1)
  assert.equal(result.confirmationDelayObservations, 2)
  assert.equal(result.injectedIntervalDetected, true)
  assert.equal('accuracy' in result, false)
})
