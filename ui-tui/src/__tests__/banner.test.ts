import { describe, expect, it } from 'vitest'

import { artWidth, inkWidth, logo, parseRichMarkup } from '../banner.js'

// Regression: `RICH_RE` lost its `/g` flag during a rewrite, and
// `String.prototype.matchAll` throws on a non-global RegExp. That crashed
// the entire TUI render the moment a skin set `banner_logo` — the
// decorative path is still the only caller, so nothing else caught it.
describe('parseRichMarkup', () => {
  const MARKUP = '[bold #FFD700]HELLO[/]\n[dim #585b70]world[/]'

  it('does not throw (matchAll requires a global RegExp)', () => {
    expect(() => parseRichMarkup(MARKUP)).not.toThrow()
  })

  it('splits styled runs into color/text pairs', () => {
    // Two lines: the \n separates them, it does not create a blank line.
    const lines = parseRichMarkup(MARKUP)

    expect(lines).toEqual([
      ['#FFD700', 'HELLO'],
      ['#585b70', 'world']
    ])
  })

  it('keeps unstyled text unstyled', () => {
    expect(parseRichMarkup('plain')).toEqual([['', 'plain']])
  })

  it('preserves unstyled text before a styled run', () => {
    expect(parseRichMarkup('pre [#ff0000]mid[/] post')).toEqual([
      ['', 'pre '],
      ['#ff0000', 'mid'],
      ['', ' post']
    ])
  })

  it('handles empty lines', () => {
    expect(parseRichMarkup('a\n\nb')).toEqual([
      ['', 'a'],
      ['', ' '],
      ['', 'b']
    ])
  })
})

describe('logo', () => {
  it('returns nothing when the skin ships no art', () => {
    expect(logo()).toEqual([])
  })

  it('renders a skin-supplied banner_logo', () => {
    expect(logo('[bold #ff0000]ART[/]')).toEqual([['#ff0000', 'ART']])
  })

  it('artWidth and inkWidth agree on unpadded art', () => {
    const lines = logo('[#ff0000]ART[/]')

    expect(artWidth(lines)).toBe(3)
    expect(inkWidth(lines)).toBe(3)
  })

  it('inkWidth ignores trailing padding', () => {
    const lines: [string, string][] = [['#ff0000', 'AB  ']]

    expect(artWidth(lines)).toBe(4)
    expect(inkWidth(lines)).toBe(2)
  })
})
