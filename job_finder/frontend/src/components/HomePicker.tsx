import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Place } from '../api/types'

type Props = { home: Place | null; onChoose: (place: Place) => void }

// Choose your home town by typing its name, in English or Hebrew. Nothing is
// chosen for you. Its English name can then be written your way ("Kfar Kana"
// rather than the list's "Kafr Kanna"): it's only a label, the position stays
// the town's.
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
  return (
    <div className="home-picker">
      {home && (
        <p className="home-current">
          <input aria-label="Your town's name" value={home.name} maxLength={100}
            onChange={(event) => onChoose({ ...home, name: event.target.value })} />
          {home.he && <span className="muted">{home.he}</span>}
          <span className="muted small">(you can write the name your way)</span>
        </p>
      )}
      <input type="search" value={query}
        placeholder={home ? 'Choose another town: type it in English or Hebrew'
          : 'Type your town in English or Hebrew'}
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
        <p className="muted small">No town found yet. Try another spelling.</p>
      )}
    </div>
  )
}
