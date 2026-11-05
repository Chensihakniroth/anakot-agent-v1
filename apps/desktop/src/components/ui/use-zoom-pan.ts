import {
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState
} from 'react'

import { isSmartZoomWheel } from '@/lib/trackpad-gestures'

interface Transform {
  scale: number
  x: number
  y: number
}

const MIN_SCALE = 0.25
const MAX_SCALE = 8
const WHEEL_STEP = 1.1
const BUTTON_STEP = 1.25
const FIT_INSET_X = 32
const FIT_INSET_Y = 64
export const FIT_MIN_SCALE = 0.05
const DRAG_THRESHOLD = 4

interface UseZoomPanOptions {
  enabled?: boolean
  maxScale?: number
  minScale?: number
}

/**
 * Headless pan/zoom transform shared by every zoomable surface. Wheel zooms
 * toward the cursor, drag pans, two-finger pinch zooms and pans, and the
 * buttons zoom toward the centre. The native wheel listener is non-passive so
 * an open viewer never scrolls the page underneath it.
 */
export function useZoomPan<T extends HTMLElement = HTMLElement>(options: UseZoomPanOptions = {}) {
  const { enabled = true, minScale = MIN_SCALE, maxScale = MAX_SCALE } = options
  const clamp = useCallback((scale: number) => Math.min(maxScale, Math.max(minScale, scale)), [minScale, maxScale])
  const ref = useRef<T>(null)
  const [node, setNode] = useState<T | null>(null)

  const refCallback = useCallback((instance: T | null) => {
    ref.current = instance
    setNode(instance)
  }, [])

  const [transform, setTransform] = useState<Transform>({ scale: 1, x: 0, y: 0 })
  const [panning, setPanning] = useState(false)
  const [moved, setMoved] = useState(false)
  const drag = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null)
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const pinch = useRef<{ dist: number; midX: number; midY: number } | null>(null)
  const [contentEl, setContentEl] = useState<HTMLDivElement | null>(null)

  const zoomAt = useCallback(
    (factor: number, cx = 0, cy = 0) => {
      setTransform(prev => {
        const scale = clamp(prev.scale * factor)
        const k = scale / prev.scale

        return { scale, x: cx - k * (cx - prev.x), y: cy - k * (cy - prev.y) }
      })
    },
    [clamp]
  )

  const fit = useCallback(() => {
    if (!node || !contentEl) {
      return
    }

    const availableW = node.clientWidth - FIT_INSET_X * 2
    const availableH = node.clientHeight - FIT_INSET_Y * 2
    const contentW = contentEl.scrollWidth
    const contentH = contentEl.scrollHeight

    if (availableW <= 0 || availableH <= 0 || contentW <= 0 || contentH <= 0) {
      return
    }

    const scale = Math.min(availableW / contentW, availableH / contentH, 1)
    setTransform({ scale: clamp(scale), x: 0, y: 0 })
  }, [clamp, contentEl, node])

  const fittedRef = useRef(true)

  const fitIfFitted = useCallback(() => {
    if (fittedRef.current) {
      fit()
    }
  }, [fit])

  useLayoutEffect(() => {
    if (!node || !contentEl || typeof ResizeObserver === 'undefined') {
      return
    }

    const observer = new ResizeObserver(fitIfFitted)
    observer.observe(node)
    observer.observe(contentEl)

    return () => observer.disconnect()
  }, [contentEl, fitIfFitted, node])

  const reset = useCallback(() => {
    setTransform({ scale: 1, x: 0, y: 0 })
    setMoved(false)
    setPanning(false)
    fittedRef.current = true
    fit()
  }, [fit])

  const zoomIn = useCallback(() => {
    fittedRef.current = false
    const current = ref.current
    const rect = current?.getBoundingClientRect()
    zoomAt(BUTTON_STEP, rect ? rect.width / 2 : 0, rect ? rect.height / 2 : 0)
  }, [zoomAt])

  const zoomOut = useCallback(() => {
    fittedRef.current = false
    const current = ref.current
    const rect = current?.getBoundingClientRect()
    zoomAt(1 / BUTTON_STEP, rect ? rect.width / 2 : 0, rect ? rect.height / 2 : 0)
  }, [zoomAt])

  // The native listener must be attached after the portal node mounts and
  // removed when the lightbox closes.
  // eslint-disable-next-line no-restricted-syntax
  useEffect(() => {
    if (!node || !enabled) {
      return
    }

    const onWheel = (event: WheelEvent) => {
      event.preventDefault()

      if (isSmartZoomWheel(event)) {
        reset()

        return
      }

      fittedRef.current = false
      const rect = node.getBoundingClientRect()
      const cx = event.clientX - rect.left - rect.width / 2
      const cy = event.clientY - rect.top - rect.height / 2
      zoomAt(event.deltaY < 0 ? WHEEL_STEP : 1 / WHEEL_STEP, cx, cy)
    }

    node.addEventListener('wheel', onWheel, { passive: false })

    return () => node.removeEventListener('wheel', onWheel)
  }, [enabled, node, reset, zoomAt])

  const endPan = useCallback(() => {
    drag.current = null
    setPanning(false)
  }, [])

  const onPointerDown = useCallback((event: ReactPointerEvent<T>) => {
    event.currentTarget.setPointerCapture?.(event.pointerId)
    pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY })
    setMoved(false)
    fittedRef.current = false

    if (pointers.current.size === 1) {
      drag.current = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY }
      pinch.current = null
    } else if (pointers.current.size === 2) {
      const [a, b] = [...pointers.current.values()]
      pinch.current = {
        dist: Math.hypot(a.x - b.x, a.y - b.y),
        midX: (a.x + b.x) / 2,
        midY: (a.y + b.y) / 2
      }
      drag.current = null
    }
  }, [])

  const onPointerMove = useCallback(
    (event: ReactPointerEvent<T>) => {
      if (!pointers.current.has(event.pointerId)) {
        return
      }

      pointers.current.set(event.pointerId, { x: event.clientX, y: event.clientY })
      const current = ref.current

      if (!current) {
        return
      }

      const rect = current.getBoundingClientRect()
      const originX = rect.width / 2
      const originY = rect.height / 2

      if (pointers.current.size >= 2 && pinch.current) {
        const [a, b] = [...pointers.current.values()]
        const dist = Math.hypot(a.x - b.x, a.y - b.y)
        const midX = (a.x + b.x) / 2
        const midY = (a.y + b.y) / 2
        const factor = dist / (pinch.current.dist || dist)

        setTransform(prev => {
          const scale = clamp(prev.scale * factor)
          const k = scale / prev.scale
          const fx = midX - rect.left - originX
          const fy = midY - rect.top - originY

          return {
            scale,
            x: prev.x + (midX - pinch.current!.midX) + (fx - k * fx),
            y: prev.y + (midY - pinch.current!.midY) + (fy - k * fy)
          }
        })

        pinch.current = { dist, midX, midY }
        setMoved(true)
        setPanning(true)

        return
      }

      if (pointers.current.size === 1 && drag.current) {
        const dx = event.clientX - drag.current.x
        const dy = event.clientY - drag.current.y

        if (Math.hypot(event.clientX - drag.current.startX, event.clientY - drag.current.startY) > DRAG_THRESHOLD) {
          setMoved(true)
          setPanning(true)
        }

        setTransform(prev => ({ ...prev, x: prev.x + dx, y: prev.y + dy }))
        drag.current = { ...drag.current, x: event.clientX, y: event.clientY }
      }
    },
    [clamp]
  )

  const onPointerUp = useCallback((event: ReactPointerEvent<T>) => {
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    pointers.current.delete(event.pointerId)
    setPanning(false)

    if (pointers.current.size === 1) {
      const [only] = [...pointers.current.values()]
      drag.current = { x: only.x, y: only.y, startX: only.x, startY: only.y }
      setMoved(true)
      pinch.current = null
    } else if (pointers.current.size === 0) {
      drag.current = null
      pinch.current = null
    }
  }, [])

  const onPointerCancel = useCallback((event: ReactPointerEvent<T>) => {
    event.currentTarget.releasePointerCapture?.(event.pointerId)
    pointers.current.delete(event.pointerId)

    if (pointers.current.size <= 1) {
      drag.current = null
      pinch.current = null
      setPanning(false)
      setMoved(false)
    }
  }, [])

  const style: CSSProperties = {
    transform: `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`
  }

  return {
    moved,
    panning,
    ref: refCallback,
    reset,
    scale: transform.scale,
    setContentEl,
    stageProps: { onPointerCancel, onPointerDown, onPointerLeave: endPan, onPointerMove, onPointerUp },
    style,
    zoomIn,
    zoomOut
  }
}
