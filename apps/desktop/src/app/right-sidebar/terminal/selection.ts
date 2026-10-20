import type { ITheme, Terminal } from '@xterm/xterm'
import type { CSSProperties } from 'react'

import { isMacPlatform } from '@/lib/platform'
import type { DesktopTerminalPalette } from '@/themes/types'

// VS Code's default integrated-terminal palette (terminalColorRegistry.ts) — a
// fixed table per theme type, not luminance-derived. Light/dark diverge on
// purpose so each stays legible (e.g. mustard yellow on white).
const DARK_THEME: ITheme = {
  background: '#1e1e1e',
  foreground: '#cccccc',
  cursor: '#cccccc',
  cursorAccent: '#1e1e1e',
  selectionBackground: '#264f7866',
  black: '#000000',
  red: '#cd3131',
  green: '#0dbc79',
  yellow: '#e5e510',
  blue: '#2472c8',
  magenta: '#bc3fbc',
  cyan: '#11a8cd',
  white: '#e5e5e5',
  brightBlack: '#666666',
  brightRed: '#f14c4c',
  brightGreen: '#23d18b',
  brightYellow: '#f5f543',
  brightBlue: '#3b8eea',
  brightMagenta: '#d670d6',
  brightCyan: '#29b8db',
  brightWhite: '#e5e5e5'
}

const LIGHT_THEME: ITheme = {
  background: '#ffffff',
  foreground: '#333333',
  cursor: '#333333',
  cursorAccent: '#ffffff',
  selectionBackground: '#add6ff80',
  black: '#000000',
  red: '#cd3131',
  green: '#00bc00',
  yellow: '#949800',
  blue: '#0451a5',
  magenta: '#bc05bc',
  cyan: '#0598bc',
  white: '#555555',
  brightBlack: '#666666',
  brightRed: '#cd3131',
  brightGreen: '#14ce14',
  brightYellow: '#b5ba00',
  brightBlue: '#0451a5',
  brightMagenta: '#bc05bc',
  brightCyan: '#0598bc',
  brightWhite: '#a5a5a5'
}

// Palette by painted mode, optionally overlaid with an imported theme's ANSI
// palette (Solarized terminal for the Solarized skin, etc.). `palette` only
// fills the slots it defines, so a partial import keeps the mode defaults for
// the rest. `background` is a fallback only — withSurface swaps in the live skin
// surface at runtime (keeping transparency); minimumContrastRatio keeps colors
// crisp against it.
export function terminalTheme(mode: 'light' | 'dark', palette?: DesktopTerminalPalette): ITheme {
  const base = mode === 'dark' ? DARK_THEME : LIGHT_THEME

  if (!palette) {
    return base
  }

  const overlay = { ...base } as Record<string, string>

  for (const [slot, value] of Object.entries(palette)) {
    if (value) {
      overlay[slot] = value
    }
  }

  return overlay as ITheme
}

// Resolve a CSS custom property (or any background color) to a concrete color
// for the WebGL renderer + contrast clamp. Custom props don't resolve via
// getComputedStyle, so probe a real background-color. Read AFTER applyTheme
// repaints (mount / rAF post-change) or it lags a frame behind.
function probeBackgroundColor(variable: string, fallback: string): string {
  if (typeof document === 'undefined' || !document.body) {
    return fallback
  }

  const probe = document.createElement('span')
  probe.style.cssText = `position:absolute;visibility:hidden;pointer-events:none;background-color:var(${variable})`
  document.body.appendChild(probe)
  const resolved = getComputedStyle(probe).backgroundColor
  probe.remove()

  // A pre-paint frame (and jsdom) hands back the unresolved `var(...)` text or
  // an empty string instead of a color; only take a real rgb/hex value. A token
  // that resolves to transparent falls back too — callers need the palette's
  // own background as the contrast reference.
  return /^(?:#[\da-f]{3,8}|rgba?\()/i.test(resolved) && resolved !== 'rgba(0, 0, 0, 0)' ? resolved : fallback
}

function resolveSurfaceColor(fallback: string): string {
  return probeBackgroundColor('--ui-terminal-surface-background', fallback)
}

/**
 * The same color with its alpha dropped to zero — xterm's canvas keeps the RGB
 * (its contrast clamp and block cursor read the channels) while the pixels stop
 * hiding whatever composites underneath.
 */
export function transparentColor(color: string): string {
  const value = color.trim()
  const hex = /^#([\da-f]{3,8})$/i.exec(value)

  if (hex) {
    const digits = hex[1]

    const channel = (index: number) =>
      parseInt(digits.length <= 4 ? digits[index].repeat(2) : digits.slice(index * 2, index * 2 + 2), 16)

    return `rgba(${channel(0)}, ${channel(1)}, ${channel(2)}, 0)`
  }

  const rgb = /^rgba?\(([^)]+)\)$/i.exec(value)

  if (!rgb) {
    return 'rgba(0, 0, 0, 0)'
  }

  const [r, g, b] = rgb[1].split(/[\s,/]+/).filter(Boolean)

  return `rgba(${Number(r) || 0}, ${Number(g) || 0}, ${Number(b) || 0}, 0)`
}

/**
 * The pair xterm needs to sit on the page: the color its canvas paints, and the
 * opaque color behind it (block cursor + contrast reference).
 *
 * Opaque surfaces take the terminal token as-is. Under window glass the page is
 * transparent but xterm paints its own canvas, so a CSS alpha on the pane never
 * reaches the cells — hand it the tint at alpha 0 instead, keeping the tint's
 * RGB as the contrast reference so ANSI colors stay clamped to the surface the
 * user actually sees.
 */
export function terminalSurface(fallback: string, glass: boolean): { accent: string; background: string } {
  if (!glass) {
    const surface = resolveSurfaceColor(fallback)

    return { accent: surface, background: surface }
  }

  const tint = probeBackgroundColor('--ui-bg-chrome', fallback)

  return { accent: tint, background: transparentColor(tint) }
}

export { isMacPlatform }

export function terminalSelectionLabel(term: Terminal, shellName: string, text: string) {
  const pos = term.getSelectionPosition()

  if (pos) {
    return pos.start.y === pos.end.y ? `${shellName}:${pos.start.y}` : `${shellName}:${pos.start.y}-${pos.end.y}`
  }

  const lines = Math.max(1, text.trim().split(/\r?\n/).length)

  return `${shellName}:${lines} line${lines === 1 ? '' : 's'}`
}

export function terminalSelectionAnchor(host: HTMLDivElement): CSSProperties | null {
  const rect = Array.from(host.querySelectorAll<HTMLElement>('.xterm-selection div'))
    .map(node => node.getBoundingClientRect())
    .filter(r => r.width > 0 && r.height > 0)
    .at(-1)

  if (!rect) {
    return null
  }

  const hostRect = host.getBoundingClientRect()
  const buttonWidth = 128
  const left = Math.min(Math.max(rect.left - hostRect.left, 8), Math.max(8, host.clientWidth - buttonWidth - 8))
  const top = Math.min(Math.max(rect.bottom - hostRect.top + 4, 8), Math.max(8, host.clientHeight - 34))

  return { left, top }
}
