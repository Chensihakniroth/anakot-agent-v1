import assert from 'node:assert/strict'

import { test } from 'vitest'

import { desktopBackendSpawnEnv, guestOnboardingEnabled, skipIntroEnabled } from './guest-onboarding'
import { buildSpawnCommand } from './remote-lifecycle'

test('skipIntroEnabled: exactly "1" in env or --skip-intro on argv skips the first-run film', () => {
  assert.equal(skipIntroEnabled([], { ANAKOT_SKIP_INTRO: '1' }), true)
  assert.equal(skipIntroEnabled(['electron', '.', '--skip-intro'], {}), true)

  assert.equal(skipIntroEnabled([], {}), false)
  assert.equal(skipIntroEnabled([], { ANAKOT_SKIP_INTRO: 'true' }), false)
})

test('guestOnboardingEnabled: exactly "1" in env or --guest-onboarding on argv turns the free tier on', () => {
  assert.equal(guestOnboardingEnabled([], { ANAKOT_GUEST_ONBOARDING: '1' }), true)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--guest-onboarding'], {}), true)

  assert.equal(guestOnboardingEnabled([], {}), false)
  assert.equal(guestOnboardingEnabled([], { ANAKOT_GUEST_ONBOARDING: 'true' }), false)
  assert.equal(guestOnboardingEnabled([], { ANAKOT_GUEST_ONBOARDING: '0' }), false)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--local'], { ANAKOT_GUEST_ONBOARDING: '' }), false)
})

test('desktopBackendSpawnEnv stamps the launch decision last and never lets an inherited value leak', () => {
  const base = {
    ANAKOT_HOME: '/tmp/home',
    ANAKOT_DESKTOP: '1',
    ANAKOT_GUEST_ONBOARDING: '1',
    PATH: '/usr/bin'
  }

  const on = desktopBackendSpawnEnv({ ...base, ANAKOT_GUEST_ONBOARDING: '0' }, true)
  assert.equal(on.ANAKOT_GUEST_ONBOARDING, '1')

  const off = desktopBackendSpawnEnv(base, false)
  assert.equal(off.ANAKOT_GUEST_ONBOARDING, '0', 'a stray inherited "1" must not turn the free tier on')

  for (const env of [on, off]) {
    assert.equal(env.ANAKOT_HOME, base.ANAKOT_HOME)
    assert.equal(env.ANAKOT_DESKTOP, base.ANAKOT_DESKTOP)
    assert.equal(env.PATH, base.PATH)
  }
})

test('remote SSH spawn command carries ANAKOT_GUEST_ONBOARDING=1 only when the launch decided on', () => {
  const on = buildSpawnCommand('/x/anakot', 'work', { logPath: '~/.anakot/log', guestOnboarding: true })
  assert.match(on, /exec env ANAKOT_DESKTOP=1 ANAKOT_GUEST_ONBOARDING=1 /)

  const off = buildSpawnCommand('/x/anakot', 'work', { logPath: '~/.anakot/log', guestOnboarding: false })
  assert.match(off, /exec env ANAKOT_DESKTOP=1 /)
  assert.doesNotMatch(off, /ANAKOT_GUEST_ONBOARDING/)

  const unset = buildSpawnCommand('/x/anakot', 'work', { logPath: '~/.anakot/log' })
  assert.doesNotMatch(unset, /ANAKOT_GUEST_ONBOARDING/)
})
