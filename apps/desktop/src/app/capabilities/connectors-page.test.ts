import { describe, expect, it } from 'vitest'

import type { ConnectorPageSnapshot } from './connectors-page'
import {
  deriveConnectorRows,
  filterConnectorRows,
  memberDisabledTools,
  memberPolicyRevision,
  setToolDisabled
} from './connectors-page'

const snapshot: ConnectorPageSnapshot = {
  accounts: [
    {
      active: true,
      alias: 'Work inbox',
      connection_id: 'gmail-1',
      connector: 'gmail',
      created_at: '2026-10-16T00:00:00Z',
      label: 'Gmail',
      status: 'active',
      updated_at: '2026-10-16T00:00:00Z'
    },
    {
      active: true,
      connection_id: 'linear-1',
      connector: 'linear',
      created_at: '2026-10-16T00:00:00Z',
      label: 'Linear',
      status: 'pending',
      updated_at: '2026-10-16T00:00:00Z'
    }
  ],
  catalog: [
    { category: 'Communication', description: 'Inbox and mail', logo_url: null, name: 'Gmail', slug: 'gmail' },
    { category: 'Work', description: 'Issues and projects', logo_url: null, name: 'Linear', slug: 'linear' }
  ],
  list: [
    {
      connector: 'gmail',
      connected: true,
      connection_status: 'active',
      enabled: true,
      gateway_disabled_tools: [],
      status_reason: null
    },
    {
      connector: 'notion',
      connected: false,
      connection_status: null,
      enabled: false,
      gateway_disabled_tools: ['NOTION_WRITE_PAGE'],
      status_reason: 'disabled'
    }
  ],
  policy: {
    effective: {
      connectors: ['gmail', 'linear'],
      issued_at_ms: 1,
      mode: 'allow',
      revision: 'rev-1',
      tools: { gmail: ['GMAIL_SEND_EMAIL'] },
      version: 1
    },
    layers: []
  }
}

describe('connector page derivation', () => {
  it('joins catalog, connection state, and account rows without dropping account-only data', () => {
    const rows = deriveConnectorRows(snapshot)

    expect(rows.map(row => row.slug)).toEqual(['Gmail', 'Linear', 'notion'].map(value => value.toLowerCase()))
    expect(rows.find(row => row.slug === 'gmail')).toMatchObject({ connected: true, enabled: true, name: 'Gmail' })
    expect(rows.find(row => row.slug === 'linear')?.accounts[0]?.status).toBe('pending')
    expect(rows.find(row => row.slug === 'notion')).toMatchObject({ connected: false, enabled: false })
  })

  it('filters by connector name, slug, or description', () => {
    const rows = deriveConnectorRows(snapshot)

    expect(filterConnectorRows(rows, 'inbox').map(row => row.slug)).toEqual(['gmail'])
    expect(filterConnectorRows(rows, 'NOTION').map(row => row.slug)).toEqual(['notion'])
  })

  it('keeps policy revision and changes only the selected tool', () => {
    const disabled = memberDisabledTools(snapshot.policy, 'gmail')

    expect(memberPolicyRevision(snapshot.policy)).toBe('rev-1')
    expect(setToolDisabled(disabled, 'GMAIL_SEND_EMAIL', true)).toEqual([])
    expect(setToolDisabled(disabled, 'GMAIL_LIST_MESSAGES', false)).toEqual([
      'GMAIL_LIST_MESSAGES',
      'GMAIL_SEND_EMAIL'
    ])
  })
})
