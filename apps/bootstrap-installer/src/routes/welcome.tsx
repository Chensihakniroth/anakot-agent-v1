import { type CSSProperties } from 'react'
import { Button } from '../components/button'
import { startInstall } from '../store'
import { ArrowRight } from 'lucide-react'

/*
 * Welcome screen.
 *
 * Mirrors the desktop's chat intro (apps/desktop/src/components/chat/intro.tsx):
 *   - ANAKOT AGENT wordmark rendered in StarAvenue, uppercase, tracked
 *   - mix-blend-plus-lighter so the type "glows" on the canvas
 *   - fit-text utility so the wordmark sizes itself to the column
 *
 * No install-path footer. The default install location is correct for
 * 99% of users; the rest will use the CLI installer with a -AnakotHome
 * flag. Showing %LOCALAPPDATA% to grandma is developer-brain.
 */
export default function Welcome() {
  return (
    <div className="anakot-fade-in flex h-full flex-col items-center justify-center gap-10 px-12 py-10">
      {/* Warm radial glow behind the wordmark */}
      <div
        className="anakot-glow pointer-events-none absolute inset-0 z-0"
        aria-hidden="true"
      />

      {/* Hero — same recipe the desktop's chat/intro.tsx uses */}
      <div className="relative z-10 w-full max-w-2xl min-w-0 text-center">
        <p
          className="fit-text mx-auto mb-4 w-full font-['StarAvenue'] uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          style={
            {
              '--fit-text-line-height': '0.9',
              '--fit-text-max': '6rem',
              '--fit-text-min': '2.5rem'
            } as CSSProperties
          }
        >
          <span>
            <span>ANAKOT AGENT</span>
          </span>
          <span aria-hidden="true">ANAKOT AGENT</span>
        </p>

        <p className="m-0 text-center text-base leading-normal tracking-tight text-muted-foreground">
          The agent that grows with you. We&rsquo;ll set things up in the
          background &mdash; takes a few minutes.
        </p>
      </div>

      <Button
        onClick={() => void startInstall()}
        size="lg"
        className="group relative z-10 inline-flex items-center gap-2 px-6"
      >
        Install Anakot
        <ArrowRight
          size={18}
          className="transition-transform group-hover:translate-x-0.5"
        />
      </Button>
    </div>
  )
}
