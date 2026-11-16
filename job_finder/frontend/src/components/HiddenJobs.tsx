import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { HiddenJob } from '../api/types'
import { matchingHidden } from '../logic/hidden'

// The jobs your preferences hide, each with the reason, and a search over them.
// Fetched only when this tab is opened, since most of the time nobody looks at it.
type Props = {
  onUnhide: (url: string) => void // bring back a job you hid yourself
}

export function HiddenJobs({ onUnhide }: Props) {
  const [hidden, setHidden] = useState<HiddenJob[] | null>(null) // null while loading
  const [search, setSearch] = useState('')
  const shown = matchingHidden(hidden ?? [], search)

  useEffect(() => {
    let current = true
    api.hidden().then((rows) => current && setHidden(rows))
    return () => { current = false }
  }, [])

  // The row goes at once; the full list takes a moment to load again.
  function undo(url: string) {
    setHidden((rows) => rows && rows.filter((row) => row.url !== url))
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
