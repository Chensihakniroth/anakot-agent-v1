/** The preload launch flag is the only gate for guided onboarding. */
export function isOnboardingEnabled(): boolean {
  // `store/onboarding-gate` evaluates this at module scope, so a Node
  // environment (no DOM, no preload bridge) must answer "off" rather than
  // throw and take every importer down with it.
  if (typeof window === 'undefined') {
    return false
  }

  return window.anakotDesktop?.guestOnboardingEnabled === true
}
