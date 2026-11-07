import type { Job } from '../api/types'
import { CHANCE_LABELS, chanceOf } from '../logic/chance'

// Where to start, with the reasons on hover. A guess from the rules (no AI
// judgement yet: the job isn't scored, or was scored before it was asked) says so.
export function ChanceBadge({ job }: { job: Job }) {
  const { chance, reasons, guess } = chanceOf(job)
  const why = reasons.join('. ')
  return (
    <span className={`badge chance ${chance}${guess ? ' guess' : ''}`}
      title={guess ? `A guess from the posting's title and years: ${why}` : why}>
      {CHANCE_LABELS[chance]}{guess && '?'}
    </span>
  )
}
