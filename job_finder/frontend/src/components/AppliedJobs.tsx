import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { AppliedJob } from '../api/types'

type Props = {
  onRemove: (job: AppliedJob) => void // untick: App saves it and reloads this tab
}

// Every job you applied to, newest first, including ones whose listing has
// closed. Fetched only when this tab is opened, like the Hidden tab.
export function AppliedJobs({ onRemove }: Props) {
  const [applied, setApplied] = useState<AppliedJob[] | null>(null) // null while loading

  useEffect(() => {
    let current = true
    api.appliedJobs().then((rows) => current && setApplied(rows))
    return () => { current = false }
  }, [])

  if (applied === null) return <p className="empty">Loading…</p>
  if (applied.length === 0) {
    return <p className="empty">No applications yet. Tick Applied on a position once you've
      applied, and it's kept here, even after the listing closes.</p>
  }

  const closed = applied.filter((job) => !job.listed).length
  return (
    <section>
      <p className="note">
        You've applied to {applied.length} position{applied.length === 1 ? '' : 's'}
        {closed > 0 && `, ${closed} of them no longer listed`}. Your preferences never hide a job
        you applied to.
      </p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Applied</th><th>Position</th><th>Company</th><th></th><th></th></tr></thead>
          <tbody>
            {applied.map((job) => (
              <tr key={job.url}>
                <td className="muted">{job.date}</td>
                <td className="wrap">
                  {job.title || <span className="muted">Title not saved</span>}
                  {!job.listed && <span className="badge closed">No longer listed</span>}
                </td>
                <td>{job.company}</td>
                <td>
                  <a href={job.apply_url} target="_blank" rel="noopener noreferrer">Link</a>
                </td>
                <td>
                  <button className="link-button" onClick={() => onRemove(job)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
