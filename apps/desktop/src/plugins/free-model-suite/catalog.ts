import type { ModelOptionProvider } from './types'

export interface FreeProviderGroup {
  models: string[]
  provider: ModelOptionProvider
}

export function isModelFree(provider: ModelOptionProvider, model: string): boolean {
  const pricing = provider.pricing?.[model]
  const normalized = model.toLowerCase()

  return Boolean(
    pricing?.free ||
    normalized.endsWith(':free') ||
    normalized.endsWith('-free') ||
    (provider.free_tier && !provider.unavailable_models?.includes(model))
  )
}

export function filterFreeModelGroups(providers: readonly ModelOptionProvider[], search = ''): FreeProviderGroup[] {
  const query = search.trim().toLowerCase()

  return providers
    .filter(provider => provider.authenticated === true)
    .map(provider => ({
      provider,
      models: (provider.models ?? []).filter(model => isModelFree(provider, model))
    }))
    .filter(group => group.models.length > 0)
    .map(group => {
      if (!query) {
        return group
      }

      const terms = query.split(/\s+/)
      const providerText = `${group.provider.name} ${group.provider.slug}`.toLowerCase()

      return {
        ...group,
        models: group.models.filter(model => {
          const modelText = model.toLowerCase()

          return terms.every(term => providerText.includes(term) || modelText.includes(term))
        })
      }
    })
    .filter(group => group.models.length > 0)
}

export function freeModelCount(groups: readonly FreeProviderGroup[]): number {
  return groups.reduce((total, group) => total + group.models.length, 0)
}
