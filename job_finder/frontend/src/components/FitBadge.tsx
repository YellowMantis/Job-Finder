import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Job } from '../api/types'
import { useCountUp } from '../hooks/useCountUp'
import { fitClass, onLinkedIn, scoreOf } from '../logic/jobs'

// The scores that have already played their arrival animation, so a score
// animates once: not again when you come back from another tab.
const arrived = new Set<string>()
const SWEEP_MS = 1600 // one pass of the "being scored" light, as in index.css
const ARRIVAL_MS = 1900 // the pop and the row glow, as in index.css

// A job's fit score in the table, or "?" / "–" when there is none. While the
// AI is scoring the job ('waiting'), a shimmering placeholder instead; when
// its score has just arrived ('new'), the score animates in.
export function FitBadge({ job, state = null }: { job: Job; state?: 'waiting' | 'new' | null }) {
  const score = scoreOf(job)

  if (state === 'waiting') return <Waiting />

  if (score === null) {
    const why = job.fit
      ? job.fit.notes.join(' ')
      : job.has_text ? 'Not scored yet'
      : onLinkedIn(job) ? "Listed on LinkedIn: there's no posting text to score against"
      : 'No posting text to score against'
    return <span className="muted" title={why}>{job.fit ? '?' : '–'}</span>
  }
  return <FitScore score={score} title={`Fit ${score}%. Scored ${job.fit!.scored} by ${job.fit!.model}`}
    arrival={state === 'new' ? `${job.url} ${job.fit!.scored}` : undefined} />
}

// The "being scored" placeholder: a light sweeping across at a steady pace.
// After every redraw (the table re-sorts every few seconds while scoring, and
// moving a row starts its animation over), the sweep is set back to the one
// shared clock, before the screen shows it: no restarts, and every
// placeholder on the same beat.
function Waiting() {
  const sweep = useRef<HTMLSpanElement>(null)
  useLayoutEffect(() => {
    const animation = sweep.current?.getAnimations()[0]
    const now = document.timeline.currentTime
    if (animation && typeof now === 'number') animation.currentTime = now % SWEEP_MS
  })
  return (
    <span className="fit-waiting" title="Being scored now" aria-label="Being scored">
      <span ref={sweep} className="fit-sweep" />
    </span>
  )
}

// The score itself: "96%" as a bold number in the fit colour (green, amber,
// grey). The same in the table and in the job panel. `arrival` names a score
// that has just come in: it pops in, counting up from 0, and its row glows
// for a moment (index.css), once.
export function FitScore({ score, title, arrival }: { score: number; title: string; arrival?: string }) {
  // Decided when the score first appears, so later redraws don't replay it.
  const [animate] = useState(() => arrival !== undefined && !arrived.has(arrival))
  useEffect(() => { if (animate && arrival) arrived.add(arrival) }, [animate, arrival])
  const shown = useCountUp(score, animate)
  // Once played, the animation class goes: the table re-sorts every few
  // seconds while scoring, and moving a row would start its animation over.
  const [playing, setPlaying] = useState(animate)
  useEffect(() => {
    if (!playing) return
    const timer = setTimeout(() => setPlaying(false), ARRIVAL_MS)
    return () => clearTimeout(timer)
  }, [playing])
  return (
    <span className={`fit-score ${fitClass(score)}${playing ? ' arriving' : ''}`} title={title}>
      {shown}<small>%</small>
    </span>
  )
}
