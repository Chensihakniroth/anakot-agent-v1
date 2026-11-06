/**
 * @anakot belongs to the default bot only while its source has no real
 * (pre-reservation) `anakot` profile. With one, the roster shows exactly one
 * @anakot — the real profile — and the default answers to @default, so a
 * typed @anakot reaches the same profile the backend's message_agent does.
 */

import { describe, expect, it, vi } from 'vitest'

import { botHandle, botMentionTag, claimDefaultHandles, mergeMultiSourceRoster, resolveRosterMentions } from './data'
import { previewKind } from './row-helpers'
import type { RosterRow } from './types'

vi.mock('@anakot/plugin-sdk', async () => {
  const { atom } = await import('nanostores')

  return { atom, host: {}, queryClient: undefined, useQuery: vi.fn(), useValue: vi.fn() }
})

vi.mock('./shared', () => ({ getPluginCtx: () => null, ID: 'anakot-bots' }))

function roster(names: string[]): RosterRow[] {
  const local = { profiles: names.map(name => ({ name })) }

  // What Electron's buildAgentRoster reports for a single local source: bare-name handles.
  const union = {
    agents: names.map(profile => ({
      connectionId: 'local',
      connectionKind: 'local' as const,
      connectionLabel: 'This device',
      handle: profile,
      profile,
      targetProfile: profile
    })),
    primaryConnectionId: 'local'
  }

  return mergeMultiSourceRoster(local, union, 'local').profiles as RosterRow[]
}

describe('the @anakot handle', () => {
  it.each([
    [['default', 'researcher'], 'default'],
    [['default', 'anakot', 'researcher'], 'anakot']
  ])('roster %j shows one @anakot and a typed @anakot reaches %s', (names, owner) => {
    const rows = roster(names)
    const handles = rows.map(row => botHandle(row.name, row))

    expect(handles.filter(handle => handle === 'anakot')).toHaveLength(1)
    expect(rows.map(row => botMentionTag(row)).filter(tag => tag === 'anakot')).toHaveLength(1)
    expect(resolveRosterMentions('@anakot ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual([owner])
  })

  it('names the default @default once a real anakot profile holds the handle', () => {
    const rows = roster(['default', 'anakot', 'researcher'])
    const byName = Object.fromEntries(rows.map(row => [row.name, botHandle(row.name, row)]))

    expect(byName).toEqual({ default: 'default', anakot: 'anakot', researcher: 'researcher' })
    expect(resolveRosterMentions('@default ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['default'])
  })

  it('keeps each source separate: a remote anakot profile does not rename the local default', () => {
    const rows = claimDefaultHandles<Partial<RosterRow>>([
      { connectionId: 'local', name: 'default' },
      { connectionId: 'mini', name: 'default' },
      { connectionId: 'mini', name: 'anakot' }
    ])

    expect(rows.map(row => botHandle(String(row.name), row))).toEqual(['anakot', 'default', 'anakot'])
  })

  it("never lets a source's stale 'anakot' handle on its default answer @anakot", () => {
    // An older backend labels its default @anakot even beside a real anakot profile.
    const rows = claimDefaultHandles<RosterRow>([
      { connectionId: 'mini', handle: 'anakot', name: 'default', remoteSource: true },
      { connectionId: 'mini', handle: 'anakot', name: 'anakot', remoteSource: true },
      { connectionId: 'local', name: 'researcher' }
    ])

    expect(resolveRosterMentions('@anakot ping', rows, { name: 'researcher' }).map(row => row.name)).toEqual(['anakot'])
  })

  it('names a DM sender in a row preview by its roster handle', () => {
    const rows = claimDefaultHandles<RosterRow>(
      ['default', 'anakot', 'researcher'].map(name => ({ connectionId: 'local', name }))
    )

    const sender = (name: string, list: RosterRow[]) =>
      previewKind(`Message from 🤖 ${name} (@x): hi`, list, 'local').fromBot

    expect([sender('default', rows), sender('anakot', rows)]).toEqual(['default', 'anakot'])
    // No real anakot profile: the default is still @anakot (#89484).
    expect(sender('default', claimDefaultHandles<RosterRow>([{ connectionId: 'local', name: 'default' }]))).toBe(
      'anakot'
    )
  })
})
