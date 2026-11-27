import { useEffect, useState } from 'react'

// A number that counts up from 0 to its value when `animate` is true (a fit
// score that has just arrived), easing out so it settles gently. Otherwise,
// or when Windows is set to reduce motion, it is simply the value.
export function useCountUp(target: number, animate: boolean, ms = 700) {
  const [shown, setShown] = useState(0)
  const [done, setDone] = useState(!animate)

  useEffect(() => {
    if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDone(true)
      return
    }
    let frame = 0
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      setShown(Math.round(target * (1 - (1 - t) ** 3))) // fast at first, then slowing
      if (t < 1) frame = requestAnimationFrame(tick)
      else setDone(true)
    }
    frame = requestAnimationFrame(tick)
    // Frames only come while the window is on screen: if it's minimized or
    // behind another window, the count would wait at 0. Whatever happens, the
    // real number shows a moment after the animation should have finished.
    const fallback = setTimeout(() => setDone(true), ms + 100)
    return () => { cancelAnimationFrame(frame); clearTimeout(fallback) }
  }, [target, animate, ms])

  return done ? target : shown
}
