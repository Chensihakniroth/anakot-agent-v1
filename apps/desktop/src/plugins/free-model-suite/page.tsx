import {
  Button,
  Codicon,
  Contribute,
  EmptyState,
  ErrorState,
  host,
  Loader,
  queryClient,
  SearchField,
  surfaceModelSwitchConfirm,
  useQuery,
  WORKSPACE_PAGE_HEADER_AREA
} from '@anakot/plugin-sdk'
import { useMemo, useState } from 'react'

import { applyModel, CATALOG_KEY, fetchCatalog } from './api'
import { filterFreeModelGroups, freeModelCount } from './catalog'
import { useFreeModels } from './i18n'
import { ModelRow } from './model-row'
import type { ModelAssignmentResult, ModelOptionProvider } from './types'

function CatalogHeader({ loading, onRefresh }: { loading: boolean; onRefresh: () => void }) {
  const copy = useFreeModels()

  return (
    <Contribute area={WORKSPACE_PAGE_HEADER_AREA} id="free-model-suite:refresh">
      <Button disabled={loading} onClick={onRefresh} size="sm" variant="ghost">
        <Codicon className={loading ? 'animate-spin' : undefined} name="refresh" size="0.75rem" />
        {copy.refresh}
      </Button>
    </Contribute>
  )
}

export function FreeModelSuitePage() {
  const copy = useFreeModels()
  const [search, setSearch] = useState('')
  const [refreshGeneration, setRefreshGeneration] = useState(0)

  const catalog = useQuery({
    queryFn: () => fetchCatalog(refreshGeneration > 0),
    queryKey: [...CATALOG_KEY, refreshGeneration]
  })

  const groups = useMemo(
    () => filterFreeModelGroups(catalog.data?.providers ?? [], search),
    [catalog.data?.providers, search]
  )

  const total = useMemo(() => freeModelCount(groups), [groups])

  const finishApply = async (provider: ModelOptionProvider, model: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['model-options'] }),
      queryClient.invalidateQueries({ queryKey: CATALOG_KEY, refetchType: 'active' })
    ])
    host.notify({ kind: 'success', message: `${copy.switched} · ${model}` })
  }

  const apply = async (provider: ModelOptionProvider, model: string) => {
    let result: ModelAssignmentResult

    try {
      result = await applyModel(provider.slug, model)
    } catch (error) {
      host.notifyError(error, copy.switchFailed)

      return
    }

    if (!result.confirm_required) {
      if (!result.ok) {
        host.notifyError(new Error(result.confirm_message || copy.switchFailed), copy.switchFailed)

        return
      }

      await finishApply(provider, model)

      return
    }

    void surfaceModelSwitchConfirm({
      confirmMessage: result.confirm_message,
      failureMessage: copy.switchFailed,
      finish: () => finishApply(provider, model),
      model,
      requestConfirmed: () => applyModel(provider.slug, model, true)
    })
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-(--ui-surface-background)">
      <CatalogHeader
        loading={catalog.isFetching}
        onRefresh={() => setRefreshGeneration(generation => generation + 1)}
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <div className="mx-auto grid w-full max-w-4xl gap-4">
          <header className="grid gap-1.5">
            <div className="flex items-center gap-2">
              <Codicon className="text-(--ui-accent)" name="leaf" size="1rem" />
              <h1 className="text-base font-semibold text-(--ui-text-primary)">{copy.title}</h1>
            </div>
            <p className="text-xs text-(--ui-text-tertiary)">{copy.description(total)}</p>
          </header>

          <SearchField
            containerClassName="w-full max-w-md"
            loading={catalog.isFetching}
            onChange={setSearch}
            placeholder={copy.search}
            value={search}
          />

          {catalog.isPending ? (
            <div className="grid min-h-56 place-items-center">
              <Loader label={copy.loading} type="lemniscate-bloom" />
            </div>
          ) : catalog.isError ? (
            <ErrorState
              description={catalog.error instanceof Error ? catalog.error.message : String(catalog.error)}
              title={copy.failed}
            >
              <Button onClick={() => void catalog.refetch()} variant="outline">
                {copy.refresh}
              </Button>
            </ErrorState>
          ) : groups.length === 0 ? (
            <EmptyState
              description={search ? copy.noResults : copy.emptyHelp}
              title={search ? copy.noResults : copy.empty}
            />
          ) : (
            <div className="grid gap-5 pb-2">
              {groups.map(group => (
                <section className="grid gap-2" key={group.provider.slug}>
                  <div className="flex items-baseline gap-2 border-b border-(--ui-stroke-secondary)/30 pb-1.5">
                    <h2 className="text-xs font-semibold text-(--ui-text-primary)">{group.provider.name}</h2>
                    <span className="font-mono text-[0.62rem] text-(--ui-text-tertiary)">
                      {group.provider.slug} · {group.models.length}
                    </span>
                    {group.provider.free_tier && (
                      <span className="ml-auto text-[0.6rem] font-semibold tracking-wide text-emerald-600 uppercase dark:text-emerald-400">
                        Free tier
                      </span>
                    )}
                  </div>
                  <div className="grid gap-1.5">
                    {group.models.map(model => (
                      <ModelRow
                        current={catalog.data?.provider === group.provider.slug && catalog.data?.model === model}
                        key={model}
                        model={model}
                        onApply={(provider, selected) => void apply(provider, selected)}
                        provider={group.provider}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}

          <p className="pb-3 text-[0.65rem] text-(--ui-text-quaternary)">{copy.footer}</p>
        </div>
      </div>
    </div>
  )
}
