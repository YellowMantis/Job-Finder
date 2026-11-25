import type { Job } from '../api/types'
import { fitClass, scoreOf } from '../logic/jobs'

// A job's fit score in the table: the number in a coloured box, with a thin
// bar underneath that fills to the score, so good matches catch the eye. "?"
// or "–" when there is none.
export function FitBadge({ job }: { job: Job }) {
  const score = scoreOf(job)

  if (score === null) {
    const why = job.fit
      ? job.fit.notes.join(' ')
      : job.has_text ? 'Not scored yet' : 'No posting text to score against'
    return <span className="muted" title={why}>{job.fit ? '?' : '–'}</span>
  }

  return (
    <span className={`fit-score ${fitClass(score)}`}
      title={`Fit ${score}%. Scored ${job.fit!.scored} by ${job.fit!.model}`}>
      {score}<small>%</small>
      <span className="fit-meter" aria-hidden="true">
        <span style={{ width: `${score}%` }} />
      </span>
    </span>
  )
}
