import type { PluginRestOptions } from '@anakot/plugin-sdk'

import type { ModelAssignmentResult, ModelCatalog, ModelProbeResult } from './types'

type Rest = <T>(path: string, opts?: PluginRestOptions) => Promise<T>

let rest: Rest | null = null

export function bindApi(call: Rest): () => void {
  rest = call

  return () => {
    rest = null
  }
}

function api<T>(path: string, opts?: PluginRestOptions): Promise<T> {
  if (!rest) {
    return Promise.reject(new Error('Free Model Suite API is not ready'))
  }

  return rest<T>(path, opts)
}

export const CATALOG_KEY = ['free-model-suite', 'catalog'] as const

export const fetchCatalog = (refresh = false) =>
  api<ModelCatalog>(`/catalog${refresh ? '?refresh=true' : ''}`, { timeoutMs: refresh ? 45_000 : 15_000 })

export const applyModel = (provider: string, model: string, confirm_expensive_model = false) =>
  api<ModelAssignmentResult>('/models', {
    body: { confirm_expensive_model, model, provider },
    method: 'POST'
  })

export const probeModel = (body: {
  max_tokens?: number
  model: string
  prompt: string
  provider: string
  system?: string
  timeout_s?: number
}) =>
  api<ModelProbeResult>('/probe', {
    body,
    method: 'POST',
    timeoutMs: 40_000
  })
