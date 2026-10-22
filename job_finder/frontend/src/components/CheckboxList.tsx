// A list of tick boxes for choosing several values. Used inside the filter
// drop-downs (MultiSelect), and on its own wherever a choice is shown in full,
// such as the setup and settings screens.

export type Option = { value: string; label?: string } // label defaults to value

type Props = {
  options: Option[]
  selected: string[]
  onChange: (selected: string[]) => void
}

export function CheckboxList({ options, selected, onChange }: Props) {
  function toggle(value: string, ticked: boolean) {
    onChange(ticked ? [...selected, value] : selected.filter((v) => v !== value))
  }

  return (
    <div className="checkbox-list">
      {options.map(({ value, label }) => (
        <label key={value}>
          <input type="checkbox" checked={selected.includes(value)}
            onChange={(event) => toggle(value, event.target.checked)} />
          {' '}{label ?? value}
        </label>
      ))}
    </div>
  )
}
