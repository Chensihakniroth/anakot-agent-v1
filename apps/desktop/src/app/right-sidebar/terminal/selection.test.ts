import { describe, expect, it } from 'vitest'

import { terminalSurface, transparentColor } from './selection'

describe('transparentColor', () => {
  it('drops the alpha from an rgb() surface and keeps its channels', () => {
    expect(transparentColor('rgb(13, 13, 14)')).toBe('rgba(13, 13, 14, 0)')
  })

  it('drops the alpha from an rgba() surface', () => {
    expect(transparentColor('rgba(13, 13, 14, 0.71)')).toBe('rgba(13, 13, 14, 0)')
  })

  it('expands a hex surface', () => {
    expect(transparentColor('#1e1e1e')).toBe('rgba(30, 30, 30, 0)')
    expect(transparentColor('#fff')).toBe('rgba(255, 255, 255, 0)')
  })

  it('falls back to clear black for an unreadable color', () => {
    expect(transparentColor('chartreuse')).toBe('rgba(0, 0, 0, 0)')
  })
})

describe('terminalSurface', () => {
  // jsdom cannot resolve var(), so both paths fall back to the palette color the
  // caller passed — exactly the pre-paint path in the app.
  it('paints the surface token solid while the window is opaque', () => {
    expect(terminalSurface('#1e1e1e', false)).toEqual({
      accent: '#1e1e1e',
      background: '#1e1e1e'
    })
  })

  it('hands glass a see-through twin of the tint', () => {
    expect(terminalSurface('#1e1e1e', true)).toEqual({
      accent: '#1e1e1e',
      background: 'rgba(30, 30, 30, 0)'
    })
  })
})
