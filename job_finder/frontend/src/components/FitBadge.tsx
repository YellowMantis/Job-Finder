import type { Job } from '../api/types'
import { fitClass, scoreOf } from '../logic/jobs'

// A job's fit score as a coloured badge, or "?" / "–" when there is none.
// Used in the table and in the side panel.
export function FitBadge({ job }: { job: Job }) {
  const score = scoreOf(job)

  if (score === null) {
    const why = job.fit
      ? job.fit.notes.join(' ')
      : job.has_text ? 'Not scored yet' : 'No posting text to score against'
    return <span className="muted" title={why}>{job.fit ? '?' : '–'}</span>
  }

  return (
    <span className={`badge fit ${fitClass(score)}`}
      title={`Scored ${job.fit!.scored} by ${job.fit!.model}`}>
      {score}%
    </span>
  )
}
