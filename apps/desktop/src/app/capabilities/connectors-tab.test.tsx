import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ConnectorsTab } from './connectors-tab'

const requestGatewayForAgent = vi.hoisted(() => vi.fn())

vi.mock('@/store/gateway', () => ({ requestGatewayForAgent }))

describe('ConnectorsTab', () => {
  beforeEach(() => {
    requestGatewayForAgent.mockImplementation(async (_connectionId, _profile, method) => {
      switch (method) {
        case 'connectors.catalog':
          return { connectors: [{ category: 'Mail', description: 'Inbox', logo_url: null, name: 'Gmail', slug: 'gmail' }] }

        case 'connectors.list':
          return {
            available: true,
            connectors: [
              {
                connector: 'gmail',
                connected: false,
                connection_status: null,
                enabled: true,
                gateway_disabled_tools: [],
                status_reason: null
              }
            ]
          }

        case 'connectors.accounts':
          return { accounts: [] }

        case 'connectors.policy.get':
          return {
            effective: { mode: 'unrestricted', revision: 'rev-1', issued_at_ms: 1, version: 1 },
            layers: []
          }

        case 'connectors.tools':
          return {
            connector: 'gmail',
            etag: 'etag-1',
            fetched_at: 1,
            source: 'network',
            stale: false,
            toolkit_version: '1',
            tools: [
              {
                categories: ['mail'],
                deprecated: false,
                description: 'Read messages',
                facet: 'read',
                hints: [],
                name: 'List messages',
                no_auth: false,
                slug: 'GMAIL_LIST_MESSAGES'
              }
            ]
          }

        default:
          throw new Error(`unexpected RPC: ${method}`)
      }
    })
  })

  afterEach(() => {
    cleanup()
    requestGatewayForAgent.mockReset()
  })

  it('loads the account-scoped catalog, state, and selected connector tools', async () => {
    render(<ConnectorsTab profile="workbot" query="" />)

    expect((await screen.findAllByText('Gmail')).length).toBeGreaterThan(0)
    expect(await screen.findByText('List messages')).toBeTruthy()
    expect(requestGatewayForAgent).toHaveBeenCalledWith(
      null,
      'workbot',
      'connectors.list',
      { owner: { type: 'account' } },
      30000,
      undefined,
      { spawnPriority: 'foreground' }
    )
    expect(requestGatewayForAgent).toHaveBeenCalledWith(
      null,
      'workbot',
      'connectors.tools',
      { slug: 'gmail' },
      30000,
      undefined,
      { spawnPriority: 'foreground' }
    )
  })

  it('shows a real recovery surface when catalog or connection state cannot load', async () => {
    requestGatewayForAgent.mockRejectedValue(new Error('backend unavailable'))

    render(<ConnectorsTab profile="workbot" query="" />)

    await waitFor(() => expect(screen.getByText('Could not load connectors.')).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Retry' })).toBeTruthy()
  })
})
