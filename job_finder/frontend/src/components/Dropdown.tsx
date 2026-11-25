import { useEffect, useRef, type KeyboardEvent } from 'react'
import { usePopover } from '../hooks/usePopover'

export type Choice<T> = { value: T; label: string }

type Props<T extends string | number> = {
  value: T
  options: Choice<T>[]
  onChange: (value: T) => void
  active?: boolean // a filter in use: drawn in blue, like the other filters in use
  disabled?: boolean
  label?: string // for screen readers, when no visible label names it
  title?: string
  className?: string // on the button, e.g. "field" to match the boxes beside it
}

// Our own drop-down for choosing one value, instead of the browser's <select>,
// whose open list Windows draws in its own style. It looks and behaves like
// the filter drop-downs (MultiSelect): the same box, the same list. Keyboard:
// arrows move through the list, Enter chooses, Esc closes.
export function Dropdown<T extends string | number>(
  { value, options, onChange, active, disabled, label, title, className }: Props<T>,
) {
  const { open, setOpen, toggle, box } = usePopover()
  const list = useRef<HTMLDivElement>(null)
  const current = options.find((option) => option.value === value)

  // On opening, the chosen value has the focus, so the arrows start from it.
  useEffect(() => {
    if (!open) return
    const chosen = list.current?.querySelector<HTMLElement>('[aria-selected="true"]')
    // preventScroll: opening a list never moves the page under you.
    ;(chosen ?? list.current?.querySelector<HTMLElement>('[role="option"]'))?.focus({ preventScroll: true })
  }, [open])

  function choose(option: Choice<T>) {
    onChange(option.value)
    setOpen(false)
    box.current?.querySelector<HTMLElement>('.multi-button')?.focus()
  }

  function onListKey(event: KeyboardEvent) {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return
    event.preventDefault()
    const items = [...(list.current?.querySelectorAll<HTMLElement>('[role="option"]') ?? [])]
    const at = items.indexOf(document.activeElement as HTMLElement)
    items[Math.max(0, Math.min(items.length - 1, at + (event.key === 'ArrowDown' ? 1 : -1)))]?.focus()
  }

  return (
    <div ref={box} className={`multi dropdown${active ? ' active' : ''}`}>
      <button type="button" className={`multi-button${className ? ` ${className}` : ''}`}
        aria-haspopup="listbox" aria-expanded={open} aria-label={label} title={title}
        disabled={disabled} onClick={toggle}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown' && !open) { event.preventDefault(); setOpen(true) }
        }}>
        {current?.label ?? ''}
      </button>
      {open && (
        <div ref={list} className="multi-list dropdown-list" role="listbox" onKeyDown={onListKey}>
          {options.map((option) => {
            const chosen = option.value === value
            return (
              <button key={String(option.value)} type="button" role="option" aria-selected={chosen}
                className={`dropdown-option${chosen ? ' chosen' : ''}`} onClick={() => choose(option)}>
                {option.label}
                {/* A tick beside the chosen one */}
                {chosen && (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                    strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12l5 5L20 7" />
                  </svg>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
