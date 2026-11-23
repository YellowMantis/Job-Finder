import { useState } from 'react'
import { api } from '../api/client'
import { useLoadedWhenShown } from '../hooks/useLoadedWhenShown'
import { matchingHidden } from '../logic/hidden'

// The jobs your preferences hide, each with the reason, and a search over them.
// Fetched only when this tab is shown and the data changed since, since most
// of the time nobody looks at it.
type Props = {
  onUnhide: (url: string) => void // bring back a job you hid yourself
  shown: boolean // this tab is the one on screen
  version: string // changes whenever what is hidden may have changed
}

export function HiddenJobs({ onUnhide, shown: onScreen, version }: Props) {
  const [hidden, setHidden] = useLoadedWhenShown(api.hidden, onScreen, version) // null while loading
  const [search, setSearch] = useState('')
  const shown = matchingHidden(hidden ?? [], search)

  // The row goes at once; the list is fetched again with the reloaded data.
  function undo(url: string) {
    setHidden((rows) => rows.filter((row) => row.url !== url))
    onUnhide(url)
  }

  return (
    <section>
      <p className="note">
        Hidden by your preferences or by you. They are kept, not deleted, and never scored.
      </p>
      <div className="filters">
        <div className="filter-row">
          <input type="search" placeholder="Search position, company or reason" value={search}
            onChange={(event) => setSearch(event.target.value)} />
          {hidden !== null && (
            <span className="muted">
              {search.trim() ? `${shown.length.toLocaleString('en-US')} of ` : ''}
              {hidden.length.toLocaleString('en-US')} hidden
            </span>
          )}
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Position</th><th>Company</th><th>Reason</th><th></th></tr></thead>
          <tbody>
            {shown.map((job, index) => (
              // Titles repeat across companies, so the position in the list is part of the key.
              <tr key={`${index}-${job.title}`}>
                <td className="wrap">{job.title}</td>
                <td>{job.company}</td>
                <td className="muted">{job.reason}</td>
                <td>
                  {job.by_you && (
                    <button className="link-button" onClick={() => undo(job.url)}>Undo</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {hidden === null && <p className="empty">Loading…</p>}
        {hidden !== null && search.trim() && shown.length === 0 && (
          <p className="empty">Nothing hidden matches "{search.trim()}".</p>
        )}
      </div>
    </section>
  )
}
