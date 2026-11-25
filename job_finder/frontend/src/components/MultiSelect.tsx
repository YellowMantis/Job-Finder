import { usePopover } from '../hooks/usePopover'
import { CheckboxList, type Option } from './CheckboxList'

type Props = {
  label: string // e.g. "Companies"; shows the count when some are ticked
  options: Option[]
  selected: string[] // nothing ticked means "all"
  onChange: (selected: string[]) => void
}

// A button that opens a list of tick boxes, for the filter bar.
export function MultiSelect({ label, options, selected, onChange }: Props) {
  const { open, toggle, box } = usePopover()

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
