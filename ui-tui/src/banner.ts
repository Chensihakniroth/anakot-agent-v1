// Global flag is REQUIRED: parseRichMarkup uses String.prototype.matchAll,
// which throws on a non-global RegExp. Stripping `/g` here crashes the
// whole TUI render the moment a skin sets `banner_logo`.
const RICH_RE = /\[(?:bold\s+)?(?:dim\s+)?(#(?:[0-9a-fA-F]{3,8}))\]([\s\S]*?)(\[\/\])/g

export function parseRichMarkup(markup: string): Line[] {
  const lines: Line[] = []

  for (const raw of markup.split('\n')) {
    const trimmed = raw.trimEnd()

    if (!trimmed) {
      lines.push(['', ' '])

      continue
    }

    const matches = [...trimmed.matchAll(RICH_RE)]

    if (!matches.length) {
      lines.push(['', trimmed])

      continue
    }

    let cursor = 0

    for (const m of matches) {
      const before = trimmed.slice(cursor, m.index)

      if (before) {
        lines.push(['', before])
      }

      lines.push([m[1]!, m[2]!])
      cursor = m.index! + m[0].length
    }

    if (cursor < trimmed.length) {
      lines.push(['', trimmed.slice(cursor)])
    }
  }

  return lines
}

/** Skin banner art, or nothing when the skin ships none. */
export const logo = (customLogo?: string): Line[] => (customLogo ? parseRichMarkup(customLogo) : [])

export const artWidth = (lines: Line[]): number => lines.reduce((m, [, t]) => Math.max(m, t.length), 0)

export const inkWidth = (lines: Line[]): number =>
  lines.reduce((m, [, t]) => Math.max(m, t.replace(/\s+$/, '').length), 0)

export type Line = [string, string]
