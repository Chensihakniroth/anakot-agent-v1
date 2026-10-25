import { type CSSProperties, type ReactNode, useLayoutEffect, useRef } from 'react'

import { cn } from '@/lib/utils'

/** How much of a clipped edge the gradient eats. */
const FADE = '1.25rem'

export interface FadeEdges {
  above: boolean
  below: boolean
}

/** The mask for a pair of clipped edges, or undefined when nothing is clipped. */
export function edgeMask({ above, below }: FadeEdges, axis: 'x' | 'y' = 'y'): string | undefined {
  if (!above && !below) {
    return undefined
  }

  const top = above ? `transparent, black ${FADE}` : 'black'
  const bottom = below ? `black calc(100% - ${FADE}), transparent` : 'black'

  return `linear-gradient(to ${axis === 'x' ? 'right' : 'bottom'}, ${top}, ${bottom})`
}

/** Which edges of a scroller currently have content clipped behind them. */
export function scrollEdges(el: Pick<HTMLElement, 'clientHeight' | 'scrollHeight' | 'scrollTop'>): FadeEdges {
  return {
    above: el.scrollTop > 1,
    below: el.scrollTop + el.clientHeight < el.scrollHeight - 1
  }
}

/**
 * A height-capped scroller whose clipped edges fade out.
 *
 * The fade is a CSS mask driven by scroll position. Unsupported browsers show
 * no fade rather than attaching a React scroll/resize listener to every list.
 */
export function FadeScroll({
  children,
  className,
  deps,
  fade,
  maxHeight = '9rem',
  pad
}: {
  children: ReactNode
  className?: string
  deps?: unknown
  fade?: string
  maxHeight?: string
  pad?: string
}) {
  const ref = useRef<HTMLDivElement>(null)

  useLayoutEffect(() => {
    if (deps !== undefined && ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [deps])

  const style = {
    maxHeight,
    ...(fade ? { '--scroll-fade-size': fade } : {}),
    ...(pad ? { '--scroll-fade-pad': pad } : {})
  } as CSSProperties

  return (
    <div className={cn('scroll-fade-y overflow-y-auto overscroll-contain', className)} ref={ref} style={style}>
      {children}
    </div>
  )
}
