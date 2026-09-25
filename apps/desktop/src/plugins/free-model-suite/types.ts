export interface ModelPricing {
  free: boolean
  input: string
  output: string
}

export interface ModelOptionProvider {
  authenticated?: boolean | null
  capabilities?: Record<string, { fast?: boolean; reasoning?: boolean }> | null
  free_tier?: boolean | null
  models?: string[] | null
  name: string
  pricing?: Record<string, ModelPricing> | null
  slug: string
  unavailable_models?: string[] | null
  warning?: string | null
}

export interface ModelCatalog {
  model?: string
  provider?: string
  providers: ModelOptionProvider[]
}

export interface ModelAssignmentResult {
  confirm_message?: string
  confirm_required?: boolean
  model: string
  ok: boolean
  provider: string
}

export interface ModelProbeResult {
  content: string
  finish_reason: null | string
  model: string
  ok: boolean
  provider: string
  reasoning: string
  tool_calls: Array<{ arguments: string; name: string }>
}
