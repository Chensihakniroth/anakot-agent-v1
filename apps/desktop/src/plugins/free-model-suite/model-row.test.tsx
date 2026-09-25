import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ModelRow } from './model-row'
import type { ModelOptionProvider } from './types'

const provider: ModelOptionProvider = {
  authenticated: true,
  models: ['vendor/model:free'],
  name: 'OpenRouter',
  pricing: { 'vendor/model:free': { free: true, input: 'free', output: 'free' } },
  slug: 'openrouter'
}

afterEach(() => vi.restoreAllMocks())

describe('Free Model Suite model row', () => {
  it('shows the raw model identity and applies the chosen provider/model pair', () => {
    const onApply = vi.fn()
    render(<ModelRow current={false} model="vendor/model:free" onApply={onApply} provider={provider} />)

    expect(screen.getByText('vendor/model:free')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    expect(onApply).toHaveBeenCalledWith(provider, 'vendor/model:free')
  })

  it('marks the configured default as current and does not offer another apply', () => {
    render(<ModelRow current model="vendor/model:free" onApply={vi.fn()} provider={provider} />)

    expect(screen.getByText('Current')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Apply' })).toBeNull()
  })
})
