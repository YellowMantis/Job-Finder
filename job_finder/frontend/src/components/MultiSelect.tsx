import { useEffect, useRef, useState } from 'react'
import { CheckboxList, type Option } from './CheckboxList'

type Props = {
  label: string // e.g. "Companies"; shows the count when some are ticked
  options: Option[]
  selected: string[] // nothing ticked means "all"
  onChange: (selected: string[]) => void
}

// A button that opens a list of tick boxes, for the filter bar.
export function MultiSelect({ label, options, selected, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  // While open, a click anywhere outside closes it. The listener is removed
  // again when it closes, so closed drop-downs cost nothing.
  useEffect(() => {
    if (!open) return
    const closeIfOutside = (event: MouseEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('click', closeIfOutside)
    return () => document.removeEventListener('click', closeIfOutside)
  }, [open])

  return (
    <div ref={box} className={`multi${selected.length ? ' active' : ''}`}>
      <button type="button" className="multi-button" aria-expanded={open}
        onClick={() => setOpen(!open)}>
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
