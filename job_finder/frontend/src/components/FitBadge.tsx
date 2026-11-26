import type { CSSProperties } from 'react'
import type { Job } from '../api/types'
import { fitClass, scoreOf } from '../logic/jobs'

// A job's fit score in the table, or "?" / "–" when there is none.
export function FitBadge({ job }: { job: Job }) {
  const score = scoreOf(job)

  if (score === null) {
    const why = job.fit
      ? job.fit.notes.join(' ')
      : job.has_text ? 'Not scored yet' : 'No posting text to score against'
    return <span className="muted" title={why}>{job.fit ? '?' : '–'}</span>
  }
  return <FitScore score={score} title={`Fit ${score}%. Scored ${job.fit!.scored} by ${job.fit!.model}`} />
}

// The score itself: the number in a circle, in the fit colour, with a ring
// around it that fills to the score, so good matches catch the eye. The same
// in the table and in the job panel. The number is centred on its own; the
// small % hangs beside it without pulling it off centre.
export function FitScore({ score, title }: { score: number; title: string }) {
  return (
    <span className={`fit-score ${fitClass(score)}${score >= 100 ? ' full' : ''}`} title={title}
      style={{ '--score': `${score}%` } as CSSProperties}>
      <span className="fit-number">{score}<small>%</small></span>
    </span>
  )
}
