import { describe, expect, it, vi } from 'vitest'

import plugin from './plugin'

function context() {
  const contributions: Array<Record<string, unknown>> = []

  return {
    ctx: {
      i18n: { register: vi.fn() },
      onDispose: vi.fn(),
      registerMany: (items: Array<Record<string, unknown>>) => {
        contributions.push(...items)

        return vi.fn()
      },
      rest: vi.fn()
    },
    contributions
  }
}

describe('Free Model Suite desktop plugin', () => {
  it('registers a first-class route, sidebar entry, and palette command', () => {
    const { ctx, contributions } = context()

    plugin.register(ctx as never)

    expect(ctx.i18n.register).toHaveBeenCalledOnce()
    expect(ctx.onDispose).toHaveBeenCalledOnce()
    expect(contributions.map(item => item.area)).toEqual(['routes', 'sidebar.nav', 'palette'])
    expect(contributions[0]).toMatchObject({ data: { path: '/free-models' }, title: 'Free Model Suite' })
    expect(contributions[1]).toMatchObject({ data: { codicon: 'leaf', label: 'Free Models', path: '/free-models' } })
  })
})
