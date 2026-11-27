import { useEffect, useRef, useState } from 'react'

// A count that glides from its old value to its new one (466 → 412 when a
// filter changes) instead of jumping, easing out so it settles gently. A new
// change mid-glide carries on from where the number is. When Windows is set
// to reduce motion, it simply changes.
export function RollingNumber({ value, ms = 450 }: { value: number; ms?: number }) {
  const [shown, setShown] = useState(value)
  const current = useRef(value) // the number on screen, also mid-glide

  useEffect(() => {
    const from = current.current
    if (from === value) return
    const settle = () => { current.current = value; setShown(value) }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return settle()
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      current.current = Math.round(from + (value - from) * (1 - (1 - t) ** 3))
      setShown(current.current)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    // Frames only come while the window is on screen: settle on the real value anyway.
    const fallback = setTimeout(settle, ms + 100)
    return () => { cancelAnimationFrame(frame); clearTimeout(fallback) }
  }, [value, ms])

  return <>{shown}</>
}
