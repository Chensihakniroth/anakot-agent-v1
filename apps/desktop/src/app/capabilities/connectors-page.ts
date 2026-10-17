import type {
  ConnectorAccountRow,
  ConnectorCatalogRow,
  ConnectorPolicyGetResult,
  ConnectorRow
} from '@anakot/shared'

export interface ConnectorPageRow {
  accounts: ConnectorAccountRow[]
  category: string
  connected: boolean
  description: string
  disabledTools: string[]
  enabled: boolean
  logoUrl: string | null
  name: string
  slug: string
  status: ConnectorRow['connection_status']
  statusReason: string | null
}

export interface ConnectorPageSnapshot {
  accounts: ConnectorAccountRow[]
  catalog: ConnectorCatalogRow[]
  list: ConnectorRow[]
  policy: ConnectorPolicyGetResult | null
}

export function connectorDisplayName(slug: string): string {
  const words = slug.replace(/[-_]+/g, ' ').trim()

  return words ? words.replace(/\b\w/g, letter => letter.toUpperCase()) : slug
}

export function deriveConnectorRows(snapshot: ConnectorPageSnapshot): ConnectorPageRow[] {
  const catalogBySlug = new Map(snapshot.catalog.map(row => [row.slug, row]))
  const listBySlug = new Map(snapshot.list.map(row => [row.connector, row]))
  const accountsBySlug = new Map<string, ConnectorAccountRow[]>()

  for (const account of snapshot.accounts) {
    const accounts = accountsBySlug.get(account.connector) ?? []
    accounts.push(account)
    accountsBySlug.set(account.connector, accounts)
  }

  const slugs = new Set([...catalogBySlug.keys(), ...listBySlug.keys(), ...accountsBySlug.keys()])

  return [...slugs]
    .map(slug => {
      const catalog = catalogBySlug.get(slug)
      const listed = listBySlug.get(slug)
      const accounts = accountsBySlug.get(slug) ?? []
      const connected = listed?.connected === true || accounts.some(account => account.active && account.status === 'active')

      return {
        accounts,
        category: catalog?.category ?? 'Other',
        connected,
        description: catalog?.description ?? '',
        disabledTools: listed?.gateway_disabled_tools ?? [],
        enabled: listed?.enabled ?? true,
        logoUrl: catalog?.logo_url ?? null,
        name: catalog?.name || connectorDisplayName(slug),
        slug,
        status: listed?.connection_status ?? (connected ? 'active' : null),
        statusReason: listed?.status_reason ?? null
      }
    })
    .sort((left, right) => left.name.localeCompare(right.name, undefined, { sensitivity: 'base' }))
}

export function filterConnectorRows(rows: readonly ConnectorPageRow[], query: string): ConnectorPageRow[] {
  const needle = query.trim().toLowerCase()

  if (!needle) {
    return [...rows]
  }

  return rows.filter(row => `${row.name} ${row.slug} ${row.description}`.toLowerCase().includes(needle))
}

export function memberDisabledTools(policy: ConnectorPolicyGetResult | null, connector: string): string[] {
  const effective = policy?.effective

  if (!effective || !('tools' in effective) || !effective.tools) {
    return []
  }

  return [...(effective.tools[connector] ?? [])]
}

export function memberPolicyRevision(policy: ConnectorPolicyGetResult | null): string | null {
  return policy?.effective.revision ?? null
}

export function setToolDisabled(disabled: readonly string[], tool: string, enabled: boolean): string[] {
  const next = new Set(disabled)

  if (enabled) {
    next.delete(tool)
  } else {
    next.add(tool)
  }

  return [...next].sort()
}
