import type { LoopSnapshot } from '@anakot/shared/gateway-events'
import { useStore } from '@nanostores/react'
import { atom } from 'nanostores'
import { useEffect, useState } from 'react'

import { $uiState } from './uiStore.js'

/** The focused session's persisted /loop state. The gateway publishes changes; the countdown is local. */
export const $loopSnapshot = atom<{ loop: LoopSnapshot | null; sid: string | null }>({ loop: null, sid: null })

export function applyLoopSnapshot(sid: string | null, loop: LoopSnapshot | null = null) {
  const previous = $loopSnapshot.get()

  if (previous.sid !== sid || JSON.stringify(previous.loop) !== JSON.stringify(loop)) {
    $loopSnapshot.set({ loop, sid })
  }
}

export interface LoopLine {
  detail: string
  glyph: string
  label: string
  prompt: string
}

/** Round up until the last minute, then show seconds so long waits do not repaint every second. */
export function countdown(seconds: number): string {
  const left = Math.max(0, Math.ceil(seconds))

  if (left < 60) {
    return `${left}s`
  }

  const minutes = Math.ceil(left / 60)
  const hours = Math.floor(minutes / 60)

  return hours ? `${hours}h${String(minutes % 60).padStart(2, '0')}m` : `${minutes}m`
}

const cadence = (loop: LoopSnapshot) => {
  if (loop.mode === 'self_paced') {
    return 'self-paced'
  }

  const seconds = loop.interval_seconds
  const every = seconds % 3600 === 0 ? `${seconds / 3600}h` : seconds % 60 === 0 ? `${seconds / 60}m` : `${seconds}s`

  return `every ${every}`
}

/** Build the single-line live-work summary for an active or paused loop. */
export function loopLine(loop: LoopSnapshot | null, nowMs = Date.now()): LoopLine | null {
  if (!loop || (loop.status !== 'active' && loop.status !== 'paused')) {
    return null
  }

  const runs = loop.times
    ? `${loop.ticks_fired}/${loop.times} runs`
    : `${loop.ticks_fired} run${loop.ticks_fired === 1 ? '' : 's'}`

  if (loop.status === 'paused') {
    const reason = loop.paused_reason ? `${loop.paused_reason} · ` : ''

    return { detail: `${reason}${runs}`, glyph: '⏸', label: 'loop paused', prompt: loop.prompt }
  }

  const remaining = loop.next_due_at - nowMs / 1000

  const when = loop.awaiting_response
    ? 'running now'
    : loop.deferred_by_goal
      ? 'deferred to the goal'
      : remaining > 0
        ? `next in ${countdown(remaining)}`
        : 'due, waiting for idle'

  return { detail: `${cadence(loop)} · ${runs} · ${when}`, glyph: '↻', label: 'loop', prompt: loop.prompt }
}

/** Recompute the countdown while the focused loop is waiting for its next wakeup. */
export function useLoopLine(): LoopLine | null {
  const snapshot = useStore($loopSnapshot)
  const { sid } = useStore($uiState)
  const loop = snapshot.sid === sid ? snapshot.loop : null
  const ticking = loop?.status === 'active' && !loop.awaiting_response
  const [line, setLine] = useState(() => loopLine(loop))

  useEffect(() => {
    const update = () =>
      setLine(previous => {
        const next = loopLine(loop)

        return JSON.stringify(previous) === JSON.stringify(next) ? previous : next
      })

    update()

    if (!ticking) {
      return
    }

    const timer = setInterval(update, 1000)

    return () => clearInterval(timer)
  }, [loop, ticking])

  return line
}
