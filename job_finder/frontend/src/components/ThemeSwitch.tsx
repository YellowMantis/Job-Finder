import { useState } from 'react'
import { api } from '../api/client'
import type { Theme } from '../api/types'

// One button in the header that switches between light and dark. It shows
// where a click takes you: a moon while light, a sun while dark. The change
// shows at once and is saved for the next start.
export function ThemeSwitch({ initial }: { initial: Theme }) {
  const [theme, setTheme] = useState<Theme>(initial)
  const next: Theme = theme === 'light' ? 'dark' : 'light'

  function change() {
    setTheme(next)
    document.documentElement.dataset.theme = next
    api.saveTheme(next).catch(() => {}) // if saving fails, it still applies until you close Veri
  }

  return (
    // data-tip: a label that shows at once on hover (a title waits about a second).
    <button className="icon-button" onClick={change}
      data-tip={next === 'dark' ? 'Dark mode' : 'Light mode'} aria-label={`Switch to ${next} mode`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        {next === 'dark'
          ? <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
          : <>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
          </>}
      </svg>
    </button>
  )
}
