import type {
  AnakotConfig,
  AnakotConfigRecord,
  ConfigSchemaResponse,
  CustomEndpointsResponse,
  CustomEndpointUpdate,
  CustomEndpointValidationResponse,
  EnvVarInfo,
  LogsResponse,
  OAuthPollResponse,
  OAuthProvidersResponse,
  OAuthStartResponse,
  OAuthSubmitResponse,
  StatusResponse
} from '@/types/anakot'

import {
  anakotApi,
  capabilityScoped,
  type ProfileScope,
  profileScoped,
  STARTUP_REQUEST_TIMEOUT_MS
} from './client'

export function getStatus(): Promise<StatusResponse> {
  return anakotApi<StatusResponse>({
    ...profileScoped(),
    path: '/api/status'
  })
}

export function getLogs(params: {
  component?: string
  file?: string
  level?: string
  lines?: number
  search?: string
}): Promise<LogsResponse> {
  const query = new URLSearchParams()

  if (params.file) {
    query.set('file', params.file)
  }

  if (typeof params.lines === 'number') {
    query.set('lines', String(params.lines))
  }

  if (params.level && params.level !== 'ALL') {
    query.set('level', params.level)
  }

  if (params.component && params.component !== 'all') {
    query.set('component', params.component)
  }

  if (params.search) {
    query.set('search', params.search)
  }

  const suffix = query.toString()

  return anakotApi<LogsResponse>({
    ...profileScoped(),
    path: suffix ? `/api/logs?${suffix}` : '/api/logs'
  })
}

export function getAnakotConfig(profile?: string): Promise<AnakotConfig> {
  return anakotApi<AnakotConfig>({
    ...profileScoped(profile),
    path: '/api/config',
    timeoutMs: STARTUP_REQUEST_TIMEOUT_MS
  })
}

export function getAnakotConfigRecord(
  profile?: ProfileScope,
  { includeDefaults = true }: { includeDefaults?: boolean } = {}
): Promise<AnakotConfigRecord> {
  return window.anakotDesktop.api<AnakotConfigRecord>({
    ...capabilityScoped(profile),
    path: includeDefaults ? '/api/config' : '/api/config?include_defaults=false'
  })
}

export function getAnakotConfigDefaults(): Promise<AnakotConfigRecord> {
  return anakotApi<AnakotConfigRecord>({
    ...profileScoped(),
    path: '/api/config/defaults',
    timeoutMs: STARTUP_REQUEST_TIMEOUT_MS
  })
}

export function getAnakotConfigSchema(profile?: null | string): Promise<ConfigSchemaResponse> {
  return anakotApi<ConfigSchemaResponse>({
    ...profileScoped(profile),
    path: '/api/config/schema'
  })
}

export function saveAnakotConfig(
  config: AnakotConfigRecord,
  profile?: null | string,
  { preserveLanguage = false }: { preserveLanguage?: boolean } = {}
): Promise<{ ok: boolean }> {
  return anakotApi<{ ok: boolean }>({
    ...profileScoped(profile),
    path: preserveLanguage ? '/api/config?preserve_language=true' : '/api/config',
    method: 'PUT',
    body: { config }
  })
}

/** Capability-scoped counterpart of saveAnakotConfig — writes the config of
 *  the profile/connection the Capabilities scope selector points at (possibly
 *  on another registered gateway), mirroring getAnakotConfigRecord. */
export function saveAnakotConfigRecord(config: AnakotConfigRecord, profile?: ProfileScope): Promise<{ ok: boolean }> {
  return window.anakotDesktop.api<{ ok: boolean }>({
    ...capabilityScoped(profile),
    path: '/api/config',
    method: 'PUT',
    body: { config }
  })
}

export function getEnvVars(profile?: null | string): Promise<Record<string, EnvVarInfo>> {
  return anakotApi<Record<string, EnvVarInfo>>({
    ...profileScoped(profile),
    path: '/api/env'
  })
}

export function setEnvVar(key: string, value: string, profile?: ProfileScope): Promise<{ ok: boolean }> {
  return window.anakotDesktop.api<{ ok: boolean }>({
    ...capabilityScoped(profile),
    path: '/api/env',
    method: 'PUT',
    body: { key, value }
  })
}

export function deleteEnvVar(key: string, profile?: ProfileScope): Promise<{ ok: boolean }> {
  return window.anakotDesktop.api<{ ok: boolean }>({
    ...capabilityScoped(profile),
    path: '/api/env',
    method: 'DELETE',
    body: { key }
  })
}

export function revealEnvVar(key: string, profile?: ProfileScope): Promise<{ key: string; value: string }> {
  return window.anakotDesktop.api<{ key: string; value: string }>({
    ...capabilityScoped(profile),
    path: '/api/env/reveal',
    method: 'POST',
    body: { key }
  })
}

export function validateProviderCredential(
  key: string,
  value: string,
  apiKey?: string
): Promise<{ ok: boolean; reachable: boolean; message: string; models?: string[]; resolved_base_url?: string }> {
  return anakotApi<{ ok: boolean; reachable: boolean; message: string; models?: string[]; resolved_base_url?: string }>({
    ...profileScoped(),
    path: '/api/providers/validate',
    method: 'POST',
    body: { key, value, api_key: apiKey ?? '' }
  })
}

export function getCustomEndpoints(): Promise<CustomEndpointsResponse> {
  return anakotApi<CustomEndpointsResponse>({
    ...profileScoped(),
    path: '/api/providers/custom-endpoints'
  })
}

export function saveCustomEndpoint(endpoint: CustomEndpointUpdate): Promise<CustomEndpointsResponse> {
  return anakotApi<CustomEndpointsResponse>({
    ...profileScoped(),
    path: '/api/providers/custom-endpoints',
    method: 'POST',
    body: endpoint
  })
}

export function validateCustomEndpoint(endpoint: CustomEndpointUpdate): Promise<CustomEndpointValidationResponse> {
  return anakotApi<CustomEndpointValidationResponse>({
    path: '/api/providers/custom-endpoints/validate',
    method: 'POST',
    body: endpoint
  })
}

export function activateCustomEndpoint(id: string): Promise<{ ok: boolean; provider: string; model: string }> {
  return anakotApi<{ ok: boolean; provider: string; model: string }>({
    ...profileScoped(),
    path: `/api/providers/custom-endpoints/${encodeURIComponent(id)}/activate`,
    method: 'POST'
  })
}

export function deleteCustomEndpoint(id: string): Promise<CustomEndpointsResponse> {
  return anakotApi<CustomEndpointsResponse>({
    ...profileScoped(),
    path: `/api/providers/custom-endpoints/${encodeURIComponent(id)}`,
    method: 'DELETE'
  })
}

export function listOAuthProviders(profile?: null | string): Promise<OAuthProvidersResponse> {
  return anakotApi<OAuthProvidersResponse>({
    ...profileScoped(profile),
    path: '/api/providers/oauth'
  })
}

export function disconnectOAuthProvider(
  providerId: string,
  profile?: null | string
): Promise<{ ok: boolean; provider: string }> {
  return anakotApi<{ ok: boolean; provider: string }>({
    ...profileScoped(profile),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}`,
    method: 'DELETE'
  })
}

export function startOAuthLogin(providerId: string, profile?: ProfileScope): Promise<OAuthStartResponse> {
  return window.anakotDesktop.api<OAuthStartResponse>({
    ...capabilityScoped(profile),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/start`,
    method: 'POST',
    body: {}
  })
}

export function submitOAuthCode(
  providerId: string,
  sessionId: string,
  code: string,
  profile?: null | string
): Promise<OAuthSubmitResponse> {
  return anakotApi<OAuthSubmitResponse>({
    ...profileScoped(profile),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/submit`,
    method: 'POST',
    body: { session_id: sessionId, code }
  })
}

export function pollOAuthSession(
  providerId: string,
  sessionId: string,
  profile?: ProfileScope
): Promise<OAuthPollResponse> {
  return window.anakotDesktop.api<OAuthPollResponse>({
    ...capabilityScoped(profile),
    path: `/api/providers/oauth/${encodeURIComponent(providerId)}/poll/${encodeURIComponent(sessionId)}`
  })
}

export function cancelOAuthSession(sessionId: string, profile?: null | string): Promise<{ ok: boolean }> {
  return anakotApi<{ ok: boolean }>({
    ...profileScoped(profile),
    path: `/api/providers/oauth/sessions/${encodeURIComponent(sessionId)}`,
    method: 'DELETE'
  })
}
