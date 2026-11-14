import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Place } from '../api/types'

type Props = { home: Place | null; onChoose: (place: Place) => void }

// Choose your home town by typing its name, in English or Hebrew. Nothing is
// chosen for you. The chosen town shows in the box, in English and Hebrew.
export function HomePicker({ home, onChoose }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Place[]>([])

  // Search a moment after typing stops, not on every key press. A late answer
  // for an older query is ignored.
  useEffect(() => {
    if (query.trim().length < 2) return
    let current = true
    const timer = setTimeout(() => {
      api.places(query).then((found) => current && setResults(found)).catch(() => {})
    }, 250)
    return () => { current = false; clearTimeout(timer) }
  }, [query])

  const showing = query.trim().length >= 2 ? results : []
  // The chosen town shows inside the box; typing there looks for another one.
  const chosen = home ? `${home.name}${home.he ? ` · ${home.he}` : ''}` : ''
  return (
    <div className="home-picker">
      <input type="search" value={query} aria-label="Where you live"
        className={home ? 'has-home' : undefined}
        title={home ? 'Type to choose another place, in English or Hebrew' : undefined}
        placeholder={home ? chosen : 'Type your city or village, in English or Hebrew'}
        onChange={(event) => setQuery(event.target.value)} />
      {showing.length > 0 && (
        <ul className="place-results">
          {showing.map((place) => (
            <li key={`${place.name}-${place.lat}`}>
              <button type="button" onClick={() => { onChoose(place); setQuery('') }}>
                {place.name}{place.he && <span className="muted"> · {place.he}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      {query.trim().length >= 2 && showing.length === 0 && (
        <p className="muted small">No place found yet. Try another spelling.</p>
      )}
    </div>
  )
}
