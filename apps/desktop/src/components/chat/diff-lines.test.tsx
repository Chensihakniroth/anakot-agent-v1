import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

// Regression coverage for #93479: a failed dynamic import of the lazily-loaded
// Shiki diff module (packaged asar/asar.unpacked path mismatch, or any other
// fetch failure) rejects the `React.lazy()` promise. React.Suspense only
// covers the *pending* state, so the rejection throws past it to the nearest
// error boundary — which in production is the whole workspace `ContribBoundary`
// — and blanks the transcript instead of degrading to the plain colored diff.
//
// The mock resolves to a component that throws the fetch error during render —
// the same way React surfaces a rejected lazy payload (a rejected import
// re-throws at render time). Do NOT throw inside the factory itself: a
// throwing factory leaves rejected promises in the vitest mocker registry,
// and under CI load one escapes as an "unhandled error during the test run"
// attributed to whichever sibling test file the worker is running (#94415).
vi.mock('./syntax-diff', () => ({
  default: () => {
    throw new Error(
      'Failed to fetch dynamically imported module: file:///Anakot.app/Contents/Resources/app.asar/dist/assets/syntax-diff-Bo0962zh.js'
    )
  }
}))

import { ErrorBoundary } from '@/components/error-boundary'

import { FileDiffPanel } from './diff-lines'

afterEach(cleanup)

const DIFF = [
  'diff --git a/file.ts b/file.ts',
  '--- a/file.ts',
  '+++ b/file.ts',
  '@@ -1,2 +1,2 @@',
  ' const a = 1',
  '-const b = 2',
  '+const b = 3'
].join('\n')

const WORKSPACE_FALLBACK_TEXT = 'workspace failed to render'

// The failure surfaces only from console.error noise, not from the assertion.
function renderQuietly(node: Parameters<typeof render>[0]) {
  const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)

  try {
    return render(node)
  } finally {
    spy.mockRestore()
  }
}

describe('FileDiffPanel survives a failed lazy syntax-diff chunk', () => {
  it('degrades to the plain colored diff instead of taking down the surrounding boundary', async () => {
    const { container } = renderQuietly(
      <ErrorBoundary fallback={() => <div>{WORKSPACE_FALLBACK_TEXT}</div>} label="workspace">
        <FileDiffPanel diff={DIFF} path="file.ts" />
      </ErrorBoundary>
    )

    // The rejection settles a tick after the initial Suspense-pending render
    // (which coincidentally shows the same plain text already) — give it
    // real time to propagate before asserting nothing regressed.
    await act(() => new Promise(resolve => setTimeout(resolve, 300)))

    expect(container.textContent).toContain('const a = 1')
    expect(container.textContent).toContain('const b = 2')
    expect(container.textContent).toContain('const b = 3')
    expect(container.textContent).not.toContain(WORKSPACE_FALLBACK_TEXT)
  })
})

// The gutter is pinned beside the code column, but it is also always on screen —
// so it must be a pass-through surface, exactly like the Preview/Source gutters.
// Three ways to break that, all guarded here: a `bg-(--ui-editor-surface-…)` fill
// (opaque chrome under glass, and in normal mode a fill that has to match the
// pane beneath), `data-glass-opaque` (swaps the token for OPAQUE chrome by
// contract), and `backdrop-blur` (hazes on a transparent Electron window because
// the filter's backdrop has no painted layer to sample).
describe('FileDiffPanel line-number gutter stays glass-transparent', () => {
  it('paints nothing of its own', () => {
    const { container } = render(<FileDiffPanel diff={DIFF} path="file.ts" showLineNumbers />)
    const gutter = container.querySelector('[data-slot="file-diff-panel"] .sticky')

    expect(gutter).not.toBeNull()
    expect(gutter!.hasAttribute('data-glass-opaque')).toBe(false)
    expect(gutter!.className).not.toContain('backdrop-blur')
    expect(gutter!.className).not.toMatch(/\bbg-/)
  })
})
