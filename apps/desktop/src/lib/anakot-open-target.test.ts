import { describe, expect, it } from 'vitest'

import {
  normalizeAnakotOpenString,
  pathFromAnakotDeepLink,
  pathFromOpenDeepLink,
  resolveAnakotOpenPath
} from './anakot-open-target'

describe('normalizeAnakotOpenString', () => {
  it('accepts hash-router paths and strips a leading hash', () => {
    expect(normalizeAnakotOpenString('/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAnakotOpenString('#/index-network/intent/1')).toBe('/index-network/intent/1')
  })

  it('maps plugin-scoped anakot:// deep links to the same path', () => {
    expect(normalizeAnakotOpenString('anakot://index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAnakotOpenString('anakot://index-network/intent/1?focus=true')).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('maps anakot://open/… deep links by stripping the open host', () => {
    expect(normalizeAnakotOpenString('anakot://open/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeAnakotOpenString('anakot://open/settings/plugins')).toBe('/settings/plugins')
  })

  it('rejects reserved anakot kinds and unsafe paths', () => {
    expect(normalizeAnakotOpenString('anakot://blueprint/morning-brief')).toBeNull()
    expect(normalizeAnakotOpenString('anakot://plugin/install')).toBeNull()
    expect(normalizeAnakotOpenString('https://example.com/x')).toBeNull()
    expect(normalizeAnakotOpenString('/../etc/passwd')).toBeNull()
    expect(normalizeAnakotOpenString('index-network')).toBeNull()
  })
})

describe('resolveAnakotOpenPath', () => {
  it('merges structured path + params', () => {
    expect(resolveAnakotOpenPath({ path: '/index-network/intent/1', params: { focus: 'true' } })).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('resolves href the same as a bare string', () => {
    expect(resolveAnakotOpenPath({ href: 'anakot://index-network/intent/1' })).toBe('/index-network/intent/1')
  })
})

describe('pathFromAnakotDeepLink', () => {
  it('builds the navigate path from a plugin-scoped deep-link payload', () => {
    expect(pathFromAnakotDeepLink('index-network', 'intent/1')).toBe('/index-network/intent/1')
  })

  it('builds the navigate path from anakot://open/… payloads', () => {
    expect(pathFromOpenDeepLink('index-network/intent/1')).toBe('/index-network/intent/1')
    expect(pathFromAnakotDeepLink('open', 'agent/42')).toBe('/agent/42')
  })

  it('ignores reserved kinds', () => {
    expect(pathFromAnakotDeepLink('blueprint', 'morning-brief')).toBeNull()
    expect(pathFromAnakotDeepLink('plugin', 'install')).toBeNull()
  })
})
