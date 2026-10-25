import { atom } from 'nanostores'

import { $activeSessionId } from '@/store/session'

/**
 * The transcript lightbox's open source, hoisted out of `ZoomableImage`.
 * Transcript rows and markdown leaves can remount while a turn streams; keeping
 * the source in a store lets the remounted row re-present its open dialog.
 */
export const $transcriptLightbox = atom<string | null>(null)

// Do not let an open preview follow the user into another session. The same
// media path can legitimately appear in two transcripts.
$activeSessionId.subscribe(() => resetTranscriptLightbox())

export function openTranscriptLightbox(src: string): void {
  if (src) {
    $transcriptLightbox.set(src)
  }
}

/** Identity-guarded: only the row owning the source can close it. */
export function closeTranscriptLightbox(src: string): void {
  if ($transcriptLightbox.get() === src) {
    $transcriptLightbox.set(null)
  }
}

export function resetTranscriptLightbox(): void {
  $transcriptLightbox.set(null)
}
