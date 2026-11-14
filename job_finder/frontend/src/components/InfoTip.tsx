import { useState, type ReactNode } from 'react'

// A small "i" beside a heading: its explanation shows while the mouse is over
// it, or after a click (for keyboards and touch screens; a second click hides it).
export function InfoTip({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <span className={`info-tip${open ? ' open' : ''}`}>
      <button type="button" className="info-tip-button" aria-label="More about this"
        aria-expanded={open} onClick={() => setOpen(!open)} onBlur={() => setOpen(false)}>
        {/* Drawn, not a letter, so every icon looks the same: a circle, a dot and a line. */}
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
          <circle cx="8" cy="8" r="7.25" fill="none" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="8" cy="4.9" r="0.95" fill="currentColor" />
          <line x1="8" y1="7.2" x2="8" y2="11.6" stroke="currentColor" strokeWidth="1.5"
            strokeLinecap="round" />
        </svg>
      </button>
      <span className="info-tip-text" role="tooltip">{children}</span>
    </span>
  )
}
