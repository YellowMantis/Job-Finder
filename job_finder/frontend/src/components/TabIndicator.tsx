import { useLayoutEffect, useRef, useState } from 'react'

// The line under the open tab, as one element that glides to the tab you
// click instead of jumping. Put it inside the row of tabs (a <nav> with the
// class "sliding", so the tabs' own line stays hidden). It measures the open
// tab (".tab.active" beside it) whenever `active` changes, and again if that
// tab's size changes (its count going from 9 to 10, the window resizing, the
// page coming back from Settings).
export function TabIndicator({ active }: { active: string }) {
  const line = useRef<HTMLSpanElement>(null)
  const [box, setBox] = useState<{ left: number; width: number } | null>(null)
  const [placed, setPlaced] = useState(false) // after the first placement, it glides

  useLayoutEffect(() => {
    const tab = line.current?.parentElement?.querySelector<HTMLElement>('.tab.active')
    if (!tab) return
    const measure = () => setBox({ left: tab.offsetLeft, width: tab.offsetWidth })
    measure()
    const watcher = new ResizeObserver(measure)
    watcher.observe(tab)
    return () => watcher.disconnect()
  }, [active])

  useLayoutEffect(() => {
    if (box && box.width > 0 && !placed) requestAnimationFrame(() => setPlaced(true))
  }, [box, placed])

  return <span ref={line} className={`tab-indicator${placed ? '' : ' instant'}`} aria-hidden="true"
    style={box ? { left: box.left, width: box.width } : { width: 0 }} />
}
