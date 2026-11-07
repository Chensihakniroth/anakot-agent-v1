/**
 * Reshow clock for the local-models campaign tips in the rotation (today: the
 * engine update). A tip ignored (timed out) may return, but on a much longer
 * clock than the rotation's: it is the same message twice, not a tour moving on.
 */

import type { LocalCatalogModel, LocalModelsStatus } from '@/types/anakot'

export const LOCAL_TIP_RESHOW_MS = 7 * 24 * 60 * 60_000

/** Due = never shown, or shown long enough ago that repeating it reads as a
 *  reminder rather than a nag. Retirement is the caller's ledger, not ours. */
export function localTipDue(now: number, shownAt: number | undefined): boolean {
  return shownAt === undefined || now - shownAt >= LOCAL_TIP_RESHOW_MS
}

/** Retirement/shown-at ledger id for the setup CTA. Not a `TipId` — the
 *  rotation never walks it. */
export const LOCAL_SETUP_TIP_ID = 'local-setup'

export const LOCAL_SETUP_RESHOW_MS = LOCAL_TIP_RESHOW_MS

/**
 * The setup CTA is conditional rather than rotating: a machine that could serve
 * a local model, on a backend that has none staged, gets one bubble on the
 * model pill. Eligibility is a pure decision over fetched state, so the policy
 * is testable without a DOM or a backend. A set-up machine never qualifies, so
 * completing setup retires the tip without any bookkeeping.
 *
 * `connectionMode` must be 'local': on a remote backend the models would run on
 * the far machine, and a bubble promising "stays on your computer" would be
 * promising someone else's computer.
 */
export function localSetupEligible(
  connectionMode: null | string,
  status: LocalModelsStatus | null,
  catalog: readonly LocalCatalogModel[] | null
): boolean {
  if (connectionMode !== 'local' || !status || !catalog) {
    return false
  }

  const needsSetup = !status.runtime_installed || status.models.length === 0

  return needsSetup && catalog.some(model => model.fits)
}

export function localSetupDue(now: number, shownAt: number | undefined): boolean {
  return shownAt === undefined || now - shownAt >= LOCAL_SETUP_RESHOW_MS
}
