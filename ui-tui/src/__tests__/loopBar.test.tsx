import { PassThrough } from 'node:stream'

import { renderSync } from '@anakot/ink'
import type { LoopSnapshot } from '@anakot/shared/gateway-events'
import React from 'react'
import stripAnsi from 'strip-ansi'
import { expect, it } from 'vitest'

import { countdown, loopLine } from '../app/loopStatus.js'
import { LoopBarView } from '../components/loopBar.js'
import { DEFAULT_THEME } from '../theme.js'

const NOW = 1_800_000_000

const loop = (patch: Partial<LoopSnapshot> = {}): LoopSnapshot => ({
  awaiting_response: false,
  created_at: NOW - 600,
  current_delay: 2700,
  deferred_by_goal: false,
  interval_seconds: 2700,
  last_fired_at: NOW - 60,
  max_ticks: 0,
  mode: 'interval',
  next_due_at: NOW + 45 * 60,
  prompt: 'check the deploy',
  status: 'active',
  ticks_fired: 1,
  times: 0,
  until: '',
  ...patch
})

it('renders the loop countdown and hides completed loops', () => {
  expect(countdown(45 * 60)).toBe('45m')
  expect(countdown(59)).toBe('59s')
  expect(countdown(0)).toBe('0s')
  expect(loopLine(loop(), NOW * 1000)?.detail).toBe('every 45m · 1 run · next in 45m')
  expect(loopLine(loop(), (NOW + 45 * 60 + 1) * 1000)?.detail).toBe('every 45m · 1 run · due, waiting for idle')
  expect(loopLine(loop({ awaiting_response: true }), NOW * 1000)?.detail).toContain('running now')
  expect(loopLine(loop({ status: 'paused', paused_reason: 'user-paused' }))).toMatchObject({
    detail: 'user-paused · 1 run',
    label: 'loop paused'
  })
  expect(loopLine(loop({ status: 'done' }))).toBeNull()

  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 10 })
  const frames: string[] = []
  stdout.on('data', chunk => frames.push(chunk.toString()))

  const view = renderSync(<LoopBarView cols={78} line={loopLine(loop(), NOW * 1000)} t={DEFAULT_THEME} />, {
    stdout: stdout as unknown as NodeJS.WriteStream,
    stdin: new PassThrough() as unknown as NodeJS.ReadStream
  })

  view.unmount()
  view.cleanup()
  expect(stripAnsi(frames.join(''))).toContain('↻ loop · every 45m · 1 run · next in 45m · check the deploy')
})
