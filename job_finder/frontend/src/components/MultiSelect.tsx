import { useEffect, useRef, useState } from 'react'
import { CheckboxList, type Option } from './CheckboxList'

type Props = {
  label: string // e.g. "Companies"; shows the count when some are ticked
  options: Option[]
  selected: string[] // nothing ticked means "all"
  onChange: (selected: string[]) => void
}

// One press can reach the button twice: a touchpad or touch screen can send a
// touch and a mouse click for the same tap, and a slow window can repeat a
// click. Two toggles that close together would open the list and shut it at
// once, so it seems not to open at all. A second toggle this soon is ignored.
const SAME_PRESS_MS = 300

// A button that opens a list of tick boxes, for the filter bar.
export function MultiSelect({ label, options, selected, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const lastToggle = useRef(0)

  function toggle(event: React.MouseEvent) {
    if (event.timeStamp - lastToggle.current < SAME_PRESS_MS) return
    lastToggle.current = event.timeStamp
    setOpen(!open)
  }

  // While open, it closes when you press anywhere outside it (including another
  // filter: a drop-down list opens on the press and sends no click), when you
  // move to another control with the keyboard, or press Esc. The listeners are
  // removed again when it closes, so closed drop-downs cost nothing.
  useEffect(() => {
    if (!open) return
    const outside = (event: Event) => !box.current?.contains(event.target as Node)
    const closeIfOutside = (event: Event) => { if (outside(event)) setOpen(false) }
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

  return (
    <div ref={box} className={`multi${selected.length ? ' active' : ''}`}>
      <button type="button" className="multi-button" aria-expanded={open} onClick={toggle}>
        {label}{selected.length > 0 && ` (${selected.length})`}
      </button>
      {open && (
        <div className="multi-list">
          <CheckboxList options={options} selected={selected} onChange={onChange} />
        </div>
      )}
    </div>
  )
}
