import { useEffect, useState } from 'react'
import { updatedLabel } from '../logic/jobs'

// "● Updated 12m ago" in the header. It redraws once a minute, so the time
// stays true while Veri is open; the exact time shows on hover.
export function UpdatedAgo({ updated }: { updated: string | null }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000)
    return () => clearInterval(timer)
  }, [])

  if (!updated) return <span className="updated-ago muted">No listings yet</span>
  return (
    <span className="updated-ago" title={`Listings downloaded ${updated}`}>
      <span className="status-dot" aria-hidden="true" />
      {updatedLabel(updated, now)}
    </span>
  )
}
