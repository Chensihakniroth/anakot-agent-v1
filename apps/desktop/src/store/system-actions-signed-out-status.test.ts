import { afterEach, describe, expect, it, vi } from 'vitest'

import type * as AnakotApi from '@/anakot'

const getStatus = vi.fn()
const anakotApi = vi.fn()
const confirm = vi.fn()

vi.mock('@/anakot', async importOriginal => ({
  ...(await importOriginal<typeof AnakotApi>()),
  getStatus: () => getStatus(),
  anakotApi: (request: unknown) => anakotApi(request)
}))

vi.mock('@/store/confirm', () => ({ confirm: (request: unknown) => confirm(request) }))

import { confirmSharedGatewayRestart } from './system-actions'

// The Webapp's body for a caller it does not count as signed in: a tab whose access token expired
// since its last gated request reads this until a gated request rotates its cookies.
const SIGNED_OUT_STATUS = { auth_required: true, gateway_running: true, overall: 'ok', version: '0.0.0' }

afterEach(() => {
  vi.resetAllMocks()
})

describe('confirmSharedGatewayRestart on a signed-out status read', () => {
  it('re-reads after a gated request and still asks before restarting the shared multiplexer', async () => {
    getStatus
      .mockResolvedValueOnce(SIGNED_OUT_STATUS)
      .mockResolvedValueOnce({ active_sessions: 0, gateway_shared_with: ['default', 'alpha'], install_id: 'i' })
    anakotApi.mockResolvedValue({})
    confirm.mockResolvedValue(true)

    await expect(confirmSharedGatewayRestart()).resolves.toEqual(['default', 'alpha'])
    expect(anakotApi).toHaveBeenCalledWith({ path: '/api/auth/me' })
    expect(confirm).toHaveBeenCalledTimes(1)
  })

  it('reads a full status once', async () => {
    getStatus.mockResolvedValueOnce({ active_sessions: 0, gateway_shared_with: null, install_id: 'i' })

    await expect(confirmSharedGatewayRestart()).resolves.toBeNull()
    expect(getStatus).toHaveBeenCalledTimes(1)
    expect(anakotApi).not.toHaveBeenCalled()
  })
})
