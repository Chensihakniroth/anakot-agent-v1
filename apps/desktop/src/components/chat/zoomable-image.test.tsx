import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { I18nProvider } from '@/i18n/context'
import { resetTranscriptLightbox } from '@/store/transcript-lightbox'

import { ZoomableImage } from './zoomable-image'

const THUMB = 'data:image/png;base64,dGh1bWJuYWls'
const FULL = 'data:image/png;base64,ZnVsbHJlc29sdXRpb24='

async function renderImage(props: React.ComponentProps<typeof ZoomableImage> = {}) {
  let result!: ReturnType<typeof render>
  await act(async () => {
    result = render(
      <I18nProvider configClient={{ getConfig: async () => ({}), saveConfig: async () => ({ ok: true }) }}>
        <ZoomableImage alt="shot" src={THUMB} {...props} />
      </I18nProvider>
    )
  })

  return result
}

function dialogImage(): HTMLImageElement {
  return within(screen.getByRole('dialog')).getByRole('img') as HTMLImageElement
}

function scaleOf(img: HTMLElement): number {
  const match = img.style.transform.match(/scale\(([0-9.]+)\)/)

  return match ? Number(match[1]) : 1
}

afterEach(() => {
  cleanup()
  resetTranscriptLightbox()
})

describe('ZoomableImage lightbox parity', () => {
  it('keeps the thumbnail inline and uses zoomSrc in the lightbox', async () => {
    await renderImage({ zoomSrc: FULL })

    fireEvent.click(screen.getByAltText('shot'))

    expect(screen.getAllByAltText('shot')[0]?.getAttribute('src')).toBe(THUMB)
    expect(dialogImage().getAttribute('src')).toBe(FULL)
    expect(screen.getByRole('dialog').getAttribute('data-variant')).toBe('media-lightbox')
  })

  it('supports zoom controls and closes only on a clean image click', async () => {
    await renderImage()
    fireEvent.click(screen.getByAltText('shot'))
    const img = dialogImage()

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /zoom in/i }))
    })
    expect(scaleOf(img)).toBeCloseTo(1.25, 5)

    await act(async () => {
      fireEvent.pointerDown(img, { clientX: 10, clientY: 10, pointerId: 1 })
      fireEvent.pointerMove(img, { clientX: 60, clientY: 10, pointerId: 1 })
      fireEvent.pointerUp(img, { clientX: 60, clientY: 10, pointerId: 1 })
    })
    expect(screen.getByRole('dialog')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /reset zoom/i }))
    fireEvent.click(img)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('re-presents an open preview after the image row remounts', async () => {
    const { unmount } = await renderImage({ zoomSrc: FULL })
    fireEvent.click(screen.getByAltText('shot'))
    expect(dialogImage().getAttribute('src')).toBe(FULL)

    unmount()
    await renderImage({ zoomSrc: FULL })

    expect(dialogImage().getAttribute('src')).toBe(FULL)
  })
})
