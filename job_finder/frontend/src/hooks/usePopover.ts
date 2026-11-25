import { useEffect, useRef, useState } from 'react'

// One press can reach a button twice: a touchpad or touch screen can send a
// touch and a mouse click for the same tap, and a slow window can repeat a
// click. Two toggles that close together would open a list and shut it at
// once, so it seems not to open at all. A second toggle this soon is ignored.
const SAME_PRESS_MS = 300

// A list that opens under its button (the filter drop-downs and Dropdown).
// While open, it closes when you press anywhere outside it (including another
// drop-down), move to another control with the keyboard, or press Esc. The
// listeners exist only while it is open, so closed lists cost nothing.
export function usePopover() {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const lastToggle = useRef(0)

  function toggle(event: React.MouseEvent) {
    if (event.timeStamp - lastToggle.current < SAME_PRESS_MS) return
    lastToggle.current = event.timeStamp
    setOpen(!open)
  }

  useEffect(() => {
    if (!open) return
    const closeIfOutside = (event: Event) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const closeOnEsc = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false) }
    document.addEventListener('pointerdown', closeIfOutside, true)
    document.addEventListener('focusin', closeIfOutside)
    document.addEventListener('keydown', closeOnEsc)
    return () => {
      document.removeEventListener('pointerdown', closeIfOutside, true)
      document.removeEventListener('focusin', closeIfOutside)
      document.removeEventListener('keydown', closeOnEsc)
    }
  }, [open])

  return { open, setOpen, toggle, box }
}
