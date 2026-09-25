import { describe, expect, it } from 'vitest'

import { filterFreeModelGroups, isModelFree } from './catalog'
import type { ModelOptionProvider } from './types'

function provider(overrides: Partial<ModelOptionProvider> = {}): ModelOptionProvider {
  return {
    authenticated: true,
    models: [],
    name: 'Provider',
    slug: 'provider',
    ...overrides
  }
}

describe('free-model classification', () => {
  it('accepts explicit free pricing and naming markers', () => {
    expect(isModelFree(provider({ pricing: { m: { input: 'free', output: 'free', free: true } } }), 'm')).toBe(true)
    expect(isModelFree(provider(), 'vendor/model:free')).toBe(true)
    expect(isModelFree(provider(), 'vendor/model-free')).toBe(true)
  })

  it('does not treat a paid provider as making all of its models free', () => {
    expect(isModelFree(provider(), 'vendor/model')).toBe(false)
  })

  it('uses free-tier availability without including models the tier cannot select', () => {
    expect(isModelFree(provider({ free_tier: true, models: ['usable'] }), 'usable')).toBe(true)
    expect(
      isModelFree(provider({ free_tier: true, unavailable_models: ['locked'], models: ['locked'] }), 'locked')
    ).toBe(false)
  })
})

describe('catalog filtering', () => {
  it('keeps authenticated provider groups, removes empty ones, and searches model/provider names', () => {
    const groups = filterFreeModelGroups(
      [
        provider({
          models: ['alpha:free', 'paid'],
          pricing: { 'alpha:free': { input: 'free', output: 'free', free: true } }
        }),
        provider({ name: 'Hidden', slug: 'hidden', authenticated: false, models: ['hidden:free'] }),
        provider({ name: 'OpenRouter', slug: 'openrouter', models: ['vendor/beta:free', 'vendor/paid'] })
      ],
      'openrouter beta'
    )

    expect(groups).toHaveLength(1)
    expect(groups[0]).toMatchObject({ provider: { slug: 'openrouter' }, models: ['vendor/beta:free'] })
  })
})
