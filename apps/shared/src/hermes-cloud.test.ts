import { describe, expect, it } from 'vitest'

import { isAnakotCloudUrl } from './anakot-cloud'

describe('isAnakotCloudUrl', () => {
  it('recognises production and staging agent hosts, nothing else', () => {
    expect(isAnakotCloudUrl('https://ares-3009.agents.nousresearch.com')).toBe(true)
    expect(isAnakotCloudUrl('https://ares--app.agents.staging-nousresearch.com/')).toBe(true)
    expect(isAnakotCloudUrl('https://agents.nousresearch.com.evil.example')).toBe(false)
    expect(isAnakotCloudUrl('https://my-box.tailnet.ts.net')).toBe(false)
    expect(isAnakotCloudUrl('not a url')).toBe(false)
    expect(isAnakotCloudUrl(undefined)).toBe(false)
  })
})
