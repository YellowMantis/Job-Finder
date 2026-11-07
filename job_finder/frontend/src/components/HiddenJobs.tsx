import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { HiddenJob } from '../api/types'

// The jobs your preferences hide, each with the reason. Fetched only when this
// tab is opened, since most of the time nobody looks at it.
type Props = {
  onUnhide: (url: string) => void // bring back a job you hid yourself
}

export function HiddenJobs({ onUnhide }: Props) {
  const [hidden, setHidden] = useState<HiddenJob[] | null>(null) // null while loading

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
        Hidden by your preferences (level, posting age and industries), or by you, with the
        reason for each. They are kept, not deleted, and are never scored. Undo brings back a
        job you hid.
      </p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Position</th><th>Company</th><th>Reason</th><th></th></tr></thead>
          <tbody>
            {(hidden ?? []).map((job, index) => (
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
      </div>
    </section>
  )
}
