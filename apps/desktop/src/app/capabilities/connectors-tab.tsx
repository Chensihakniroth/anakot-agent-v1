import { type AccountOwner, JsonRpcGatewayError } from '@anakot/shared'
import type {
  ConnectionOperationStatus,
  ConnectorAccountsResult,
  ConnectorPolicyGetResult,
  ConnectorPolicySetResult,
  ConnectorsCatalogResult,
  ConnectorsConnectResult,
  ConnectorsListResult,
  ConnectorToolsResult
} from '@anakot/shared'
import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { type ProfileScope } from '@/anakot'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConnectorLogo } from '@/components/ui/connector-logo'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/i18n'
import { RefreshCw } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { confirm } from '@/store/confirm'
import { requestGatewayForAgent } from '@/store/gateway'
import { notifyError } from '@/store/notifications'
import { $activeGatewayProfile, normalizeProfileKey } from '@/store/profile'

import { DetailColumn, ListColumn, ListStrip, MasterDetail } from '../master-detail'

import {
  type ConnectorPageRow,
  type ConnectorPageSnapshot,
  deriveConnectorRows,
  filterConnectorRows,
  memberDisabledTools,
  memberPolicyRevision,
  setToolDisabled
} from './connectors-page'
import { CapabilityEmpty, DetailHeader } from './primitives'

interface ConnectorOperation {
  deadlineAt: number
  id: string
  slug: string
}

interface ToolsState {
  data: ConnectorToolsResult | null
  error: Error | null
  loading: boolean
}

const ACCOUNT_OWNER: AccountOwner = { type: 'account' }

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback
}

function isPolicyConflict(error: unknown): boolean {
  const reason =
    error instanceof JsonRpcGatewayError && typeof error.data === 'object' && error.data
      ? (error.data as { reason?: unknown }).reason
      : undefined

  return reason === 'POLICY_CONFLICT' || (error instanceof Error && /policy (?:changed|conflict)/i.test(error.message))
}

function statusVariant(status: ConnectorPageRow['status'], connected: boolean): 'default' | 'muted' | 'success' | 'warn' {
  if (connected || status === 'active') {
    return 'success'
  }

  if (status === 'pending') {
    return 'warn'
  }

  return 'muted'
}

function statusText(
  copy: ReturnType<typeof useI18n>['t']['connectorsPage'],
  row: ConnectorPageRow
): string {
  if (row.connected) {
    return copy.connected
  }

  if (row.status === 'pending') {
    return copy.pending
  }

  if (row.statusReason) {
    return row.statusReason
  }

  return copy.notConnected
}

export function ConnectorsTab({ profile, query }: { profile: ProfileScope; query: string }) {
  const { t } = useI18n()
  const copy = t.connectorsPage
  const activeProfile = useStore($activeGatewayProfile)

  const profileKey = normalizeProfileKey(
    typeof profile === 'object' && profile ? profile.profile ?? activeProfile : profile ?? activeProfile
  )

  const connectionId = profile && typeof profile === 'object' ? profile.connectionId ?? null : null

  const request = useCallback(
    <T,>(method: string, params: Record<string, unknown> = {}, timeoutMs = 30_000): Promise<T> =>
      requestGatewayForAgent<T>(connectionId, profileKey, method, params, timeoutMs, undefined, {
        spawnPriority: 'foreground'
      }),
    [connectionId, profileKey]
  )

  const [snapshot, setSnapshot] = useState<ConnectorPageSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [policyBusy, setPolicyBusy] = useState<string | null>(null)
  const [operation, setOperation] = useState<ConnectorOperation | null>(null)
  const [toolsRefresh, setToolsRefresh] = useState<{ count: number; slug: string } | null>(null)
  const [tools, setTools] = useState<ToolsState>({ data: null, error: null, loading: false })
  const loadGeneration = useRef(0)

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current
    setLoading(true)
    setLoadError(null)

    try {
      const [catalog, list, accounts, policy] = await Promise.all([
        request<ConnectorsCatalogResult>('connectors.catalog').catch(() => null),
        request<ConnectorsListResult>('connectors.list', { owner: ACCOUNT_OWNER }).catch(() => null),
        request<ConnectorAccountsResult>('connectors.accounts').catch(() => null),
        request<ConnectorPolicyGetResult>('connectors.policy.get').catch(() => null)
      ])

      if (!catalog || !list) {
        throw new Error(copy.loadFailed)
      }

      if (generation !== loadGeneration.current) {
        return
      }

      setSnapshot({
        accounts: accounts?.accounts ?? [],
        catalog: catalog.connectors,
        list: list.connectors,
        policy
      })
    } catch (error) {
      if (generation !== loadGeneration.current) {
        return
      }

      setSnapshot(null)
      setLoadError(errorMessage(error, copy.loadFailed))
    } finally {
      if (generation === loadGeneration.current) {
        setLoading(false)
      }
    }
  }, [copy.loadFailed, request])

  useEffect(() => {
    void load()
  }, [load])

  const rows = useMemo(() => (snapshot ? deriveConnectorRows(snapshot) : []), [snapshot])
  const visibleRows = useMemo(() => filterConnectorRows(rows, query), [query, rows])
  const selected = visibleRows.find(row => row.slug === selectedSlug) ?? rows.find(row => row.slug === selectedSlug) ?? rows[0] ?? null

  useEffect(() => {
    if (selected && selected.slug !== selectedSlug) {
      setSelectedSlug(selected.slug)
    }
  }, [selected, selectedSlug])

  useEffect(() => {
    const selectedSlugForTools = selected?.slug ?? null

    if (!selectedSlugForTools) {
      setTools({ data: null, error: null, loading: false })

      return
    }

    let cancelled = false
    const refresh = toolsRefresh?.slug === selectedSlugForTools
    setTools({ data: null, error: null, loading: true })

    void request<ConnectorToolsResult>('connectors.tools', {
      slug: selectedSlugForTools,
      ...(refresh ? { refresh: true } : {})
    })
      .then(data => {
        if (!cancelled) {
          setTools({ data, error: null, loading: false })
        }
      })
      .catch(error => {
        if (!cancelled) {
          setTools({ data: null, error: error instanceof Error ? error : new Error(String(error)), loading: false })
        }
      })

    return () => {
      cancelled = true
    }
  }, [request, selected?.slug, toolsRefresh])

  useEffect(() => {
    if (!operation) {
      return
    }

    let cancelled = false

    const poll = async () => {
      while (!cancelled && Date.now() / 1000 < operation.deadlineAt) {
        try {
          const status = await request<ConnectionOperationStatus>('connectors.operation.status', {
            op_id: operation.id,
            owner: ACCOUNT_OWNER
          })

          if (status.settled) {
            if (!cancelled) {
              setOperation(null)
              void load()
            }

            return
          }
        } catch {
          // A transient status failure should not discard a live sign-in operation.
        }

        await new Promise(resolve => setTimeout(resolve, 1000))
      }

      if (!cancelled) {
        setOperation(null)
        void load()
      }
    }

    void poll()

    return () => {
      cancelled = true
    }
  }, [load, operation, request])

  const startConnect = async (row: ConnectorPageRow): Promise<void> => {
    setBusy(row.slug)

    try {
      const result = await request<ConnectorsConnectResult>('connectors.connect', {
        connectors: [row.slug],
        owner: ACCOUNT_OWNER,
        reconnect: row.connected
      })

      const target = result.targets.find(candidate => candidate.name === row.slug)

      if (target?.connect_url) {
        void window.anakotDesktop?.openExternal?.(target.connect_url)
      }

      if (!result.settled && result.deadline_at > 0) {
        setOperation({ deadlineAt: result.deadline_at, id: result.op_id, slug: row.slug })
      } else {
        await load()
      }
    } catch (error) {
      notifyError(error, copy.connectFailed)
    } finally {
      setBusy(null)
    }
  }

  const changeConnectorPolicy = async (row: ConnectorPageRow, enabled: boolean): Promise<void> => {
    const expectedRevision = memberPolicyRevision(snapshot?.policy ?? null)

    if (!expectedRevision) {
      notifyError(new Error(copy.policyUnavailable), copy.policyUnavailable)

      return
    }

    setPolicyBusy(row.slug)

    try {
      await request<ConnectorPolicySetResult>('connectors.policy.set', {
        change: { connector: row.slug, enabled, type: 'connector' },
        expected_revision: expectedRevision
      })
      await load()
    } catch (error) {
      if (isPolicyConflict(error)) {
        await load()
        notifyError(error, copy.policyConflict)
      } else {
        notifyError(error, copy.policyFailed)
      }
    } finally {
      setPolicyBusy(null)
    }
  }

  const changeToolPolicy = async (row: ConnectorPageRow, slug: string, enabled: boolean): Promise<void> => {
    const expectedRevision = memberPolicyRevision(snapshot?.policy ?? null)

    if (!expectedRevision) {
      notifyError(new Error(copy.policyUnavailable), copy.policyUnavailable)

      return
    }

    setPolicyBusy(slug)

    try {
      const disabled = setToolDisabled(memberDisabledTools(snapshot?.policy ?? null, row.slug), slug, enabled)

      await request<ConnectorPolicySetResult>('connectors.policy.set', {
        change: { connector: row.slug, disabled_tools: disabled, type: 'tools' },
        expected_revision: expectedRevision
      })
      await load()
    } catch (error) {
      if (isPolicyConflict(error)) {
        await load()
        notifyError(error, copy.policyConflict)
      } else {
        notifyError(error, copy.policyFailed)
      }
    } finally {
      setPolicyBusy(null)
    }
  }

  const removeAccount = async (accountId: string): Promise<void> => {
    const account = snapshot?.accounts.find(candidate => candidate.connection_id === accountId)

    if (!account || !(await confirm({
      confirmLabel: copy.disconnect,
      destructive: true,
      title: copy.disconnectConfirm(account.alias || account.label)
    }))) {
      return
    }

    setBusy(`remove:${accountId}`)

    try {
      await request('connectors.accounts.remove', { connection_id: accountId })
      await load()
    } catch (error) {
      notifyError(error, copy.disconnectFailed)
    } finally {
      setBusy(null)
    }
  }

  if (loading && !snapshot) {
    return <div className="flex h-full items-center justify-center text-sm text-muted-foreground">{copy.loading}</div>
  }

  if (loadError && !snapshot) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
        <p className="text-sm text-muted-foreground">{loadError}</p>
        <Button onClick={() => void load()} size="xs" variant="secondary">
          {copy.retry}
        </Button>
      </div>
    )
  }

  if (rows.length === 0 || visibleRows.length === 0) {
    return <CapabilityEmpty noun={copy.title} query={query} />
  }

  return (
    <MasterDetail resizeId="capabilities-connectors-split" split="wide">
      <ListColumn
        header={
          <ListStrip
            left={<span className="pl-2 text-[0.68rem] font-medium text-muted-foreground">{copy.title}</span>}
            right={
              <Button aria-label={copy.refresh} className="size-5 p-0" onClick={() => void load()} size="icon" variant="ghost">
                <RefreshCw className="size-3" />
              </Button>
            }
          />
        }
      >
        {visibleRows.map(row => (
          <div className="flex items-center" key={row.slug}>
            <button
              className={cn(
                'flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left',
                selected?.slug === row.slug && 'bg-(--ui-row-active-background)'
              )}
              onClick={() => setSelectedSlug(row.slug)}
              type="button"
            >
              <ConnectorLogo className="size-5 shrink-0 rounded" connector={{ name: row.slug, title: row.name, url: row.logoUrl }} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium">{row.name}</span>
                <span className="block truncate text-[0.65rem] text-muted-foreground">{statusText(copy, row)}</span>
              </span>
            </button>
            <Switch
              aria-label={row.enabled ? copy.disable(row.name) : copy.enable(row.name)}
              checked={row.enabled}
              className="mr-1 shrink-0"
              disabled={policyBusy !== null || snapshot?.policy === null}
              onCheckedChange={enabled => void changeConnectorPolicy(row, enabled)}
              size="xs"
            />
          </div>
        ))}
      </ListColumn>
      <DetailColumn footer={copy.scopeNote}>
        {selected ? (
          <ConnectorDetail
            busy={busy}
            copy={copy}
            onConnect={() => void startConnect(selected)}
            onRefreshTools={() =>
              setToolsRefresh(value => ({ count: (value?.count ?? 0) + 1, slug: selected.slug }))
            }
            onRemoveAccount={accountId => void removeAccount(accountId)}
            onToolToggle={(slug, enabled) => void changeToolPolicy(selected, slug, enabled)}
            operation={operation?.slug === selected.slug ? operation : null}
            policy={snapshot?.policy ?? null}
            row={selected}
            tools={tools}
            toolsDisabled={memberDisabledTools(snapshot?.policy ?? null, selected.slug)}
            toolsPolicyBusy={policyBusy}
          />
        ) : null}
      </DetailColumn>
    </MasterDetail>
  )
}

function ConnectorDetail({
  busy,
  copy,
  onConnect,
  onRefreshTools,
  onRemoveAccount,
  onToolToggle,
  operation,
  policy,
  row,
  tools,
  toolsDisabled,
  toolsPolicyBusy
}: {
  busy: string | null
  copy: ReturnType<typeof useI18n>['t']['connectorsPage']
  onConnect: () => void
  onRefreshTools: () => void
  onRemoveAccount: (accountId: string) => void
  onToolToggle: (slug: string, enabled: boolean) => void
  operation: ConnectorOperation | null
  policy: ConnectorPolicyGetResult | null
  row: ConnectorPageRow
  tools: ToolsState
  toolsDisabled: string[]
  toolsPolicyBusy: string | null
}) {
  return (
    <>
      <DetailHeader
        description={row.description || row.category}
        pills={
          <Badge size="xs" variant={statusVariant(row.status, row.connected)}>
            {statusText(copy, row)}
          </Badge>
        }
        title={row.name}
      />

      <div className="flex flex-wrap items-center gap-2">
        <Button disabled={busy !== null || operation !== null} onClick={onConnect} size="xs">
          {row.connected ? copy.reconnect : copy.connect}
        </Button>
        {operation ? <span className="text-xs text-muted-foreground">{copy.waiting}</span> : null}
        {!policy ? <span className="text-xs text-muted-foreground">{copy.policyReadOnly}</span> : null}
      </div>

      <section className="grid gap-2">
        <h4 className="text-xs font-semibold">{copy.accounts}</h4>
        {row.accounts.length === 0 ? (
          <p className="text-xs text-muted-foreground">{copy.noAccounts}</p>
        ) : (
          row.accounts.map(account => (
            <div className="flex items-center gap-2 rounded-md border border-(--ui-stroke-tertiary) px-2.5 py-2" key={account.connection_id}>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium">{account.alias || account.label}</span>
                <span className="block text-[0.68rem] text-muted-foreground">{account.status}</span>
              </span>
              <Button
                disabled={busy === `remove:${account.connection_id}`}
                onClick={() => onRemoveAccount(account.connection_id)}
                size="xs"
                variant="ghost"
              >
                {copy.disconnect}
              </Button>
            </div>
          ))
        )}
      </section>

      <section className="grid gap-2">
        <div className="flex items-center gap-2">
          <h4 className="flex-1 text-xs font-semibold">{copy.tools}</h4>
          <Button disabled={tools.loading} onClick={onRefreshTools} size="xs" variant="ghost">
            {copy.refreshTools}
          </Button>
        </div>
        {tools.loading ? <p className="text-xs text-muted-foreground">{copy.loading}</p> : null}
        {tools.error ? <p className="text-xs text-destructive">{copy.toolsFailed}</p> : null}
        {!tools.loading && !tools.error && tools.data?.tools.length === 0 ? (
          <p className="text-xs text-muted-foreground">{copy.noTools}</p>
        ) : null}
        {tools.data?.stale ? <p className="text-xs text-amber-600">{copy.staleTools}</p> : null}
        <div className="grid gap-1">
          {tools.data?.tools.map(tool => {
            const locked = row.disabledTools.includes(tool.slug)
            const enabled = !toolsDisabled.includes(tool.slug)

            return (
              <div className="flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-(--ui-row-hover-background)" key={tool.slug}>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs">{tool.name || tool.slug}</span>
                  <span className="block truncate text-[0.65rem] text-muted-foreground">{tool.description}</span>
                </span>
                <Switch
                  aria-label={enabled ? copy.disable(tool.name || tool.slug) : copy.enable(tool.name || tool.slug)}
                  checked={enabled}
                  disabled={locked || policy === null || toolsPolicyBusy !== null}
                  onCheckedChange={next => onToolToggle(tool.slug, next)}
                  size="xs"
                />
              </div>
            )
          })}
        </div>
      </section>
    </>
  )
}
