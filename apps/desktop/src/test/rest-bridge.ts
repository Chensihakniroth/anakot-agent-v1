import { vi } from 'vitest'

import type { AnakotApiRequest } from '@/global'

/** Install a fake `window.anakotDesktop.api`, the preload bridge every REST helper sends through. */
export function installRestBridge(answer: (request: AnakotApiRequest) => object) {
  const api = vi.fn(async (request: AnakotApiRequest) => answer(request))

  Object.defineProperty(window, 'anakotDesktop', { configurable: true, value: { api } })

  return api
}
