import { stringWidth, Text } from '@anakot/ink'
import { useStore } from '@nanostores/react'

import { type LoopLine, useLoopLine } from '../app/loopStatus.js'
import { $uiState } from '../app/uiStore.js'
import { compactPreview } from '../lib/text.js'
import type { Theme } from '../theme.js'

/** One live-work row for a standing /loop, with a local countdown to the next wakeup. */
export function LoopBarView({ cols, line, t }: { cols: number; line: LoopLine | null; t: Theme }) {
  if (!line) {
    return null
  }

  const head = `${line.glyph} ${line.label} · ${line.detail} · `

  return (
    <Text wrap="truncate-end">
      <Text color={line.glyph === '↻' ? t.color.accent : t.color.warn}>{`${line.glyph} ${line.label}`}</Text>
      <Text color={t.color.muted}>{` · ${line.detail} · `}</Text>
      <Text color={t.color.text}>{compactPreview(line.prompt, Math.max(8, cols - stringWidth(head)))}</Text>
    </Text>
  )
}

export function LoopBar({ cols }: { cols: number }) {
  const { theme } = useStore($uiState)

  return <LoopBarView cols={cols} line={useLoopLine()} t={theme} />
}
