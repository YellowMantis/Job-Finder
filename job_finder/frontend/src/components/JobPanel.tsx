import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Fit, Job, Match } from '../api/types'
import { ageInDays, ageLabel, distanceText, fitClass, placeOf } from '../logic/jobs'

type Props = {
  job: Job
  onClose: () => void
  // Score just this job (again: it has a score; redo it, e.g. with another AI).
  // Missing when there is nothing to score with (no CV or no AI).
  onScore?: (again: boolean) => void
  scoring: boolean // a scoring run is under way
}

// The panel that slides in when you click a position: its fit review and the
// full posting text, which is fetched now, for this one job.
export function JobPanel({ job, onClose, onScore, scoring }: Props) {
  // The last text loaded, and which job it belongs to. While another job's text
  // is still arriving, the one shown doesn't match, so the panel says "Loading".
  const [loaded, setLoaded] = useState<{ url: string; text: string } | null>(null)
  const text = loaded?.url === job.url ? loaded.text : null

  useEffect(() => {
    if (!job.has_text) return
    // If you open another job before this text arrives, ignore the late answer.
    let current = true
    api.posting(job.url)
      .then(({ text }) => current && setLoaded({ url: job.url, text }))
      .catch(() => current &&
        setLoaded({ url: job.url, text: 'The posting text could not be loaded.' }))
    return () => { current = false }
  }, [job.url, job.has_text])

  // Esc closes the panel. The listener exists only while the panel is open.
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <aside className="panel" aria-label={job.title}>
      <button className="panel-close" aria-label="Close" onClick={onClose}>×</button>
      <h2>{job.title}</h2>
      <p className="panel-meta">
        {job.company} · {placeOf(job)} · {distanceText(job)} · updated {ageLabel(ageInDays(job))}
        {job.source && ` · text from ${job.source}`}
      </p>
      <div className="panel-actions">
        <a className="button" href={job.apply_url} target="_blank" rel="noopener noreferrer">
          Open posting
        </a>
        {onScore && job.has_text && (
          <button className="button secondary" disabled={scoring}
            onClick={() => onScore(Boolean(job.fit))}>
            {scoring ? 'Scoring…' : job.fit ? 'Score again' : 'Score this job'}
          </button>
        )}
      </div>

      {job.fit && <FitReview fit={job.fit} />}

      <h3 className="panel-heading">Posting</h3>
      <pre className="panel-text">
        {!job.has_text
          ? "The full posting text isn't available for this company yet. Open the posting to read it."
          : text ?? 'Loading the posting text…'}
      </pre>
    </aside>
  )
}

const SYMBOLS: Record<Match, string> = { yes: '✓', partial: '~', no: '✗' }
const IMPORTANCE: Record<string, string> = { core: ' (core of the role)', nice: ' (nice to have)' }

// The score, its summary, and every requirement with the evidence from your CV.
function FitReview({ fit }: { fit: Fit }) {
  return (
    <section className="fit-box">
      <h3>
        {fit.score === null
          ? 'No score for'
          : <span className={`badge fit ${fitClass(fit.score)}`}>{fit.score}%</span>}
        {' '}fit
      </h3>
      <p>{fit.summary}</p>
      {fit.notes.length > 0 && <p className="fit-notes">{fit.notes.join(' ')}</p>}
      <ul className="requirements">
        {fit.requirements.map((item) => (
          <li key={item.requirement} className={item.match}>
            <span className="symbol">{SYMBOLS[item.match]}</span>
            <div>
              <strong>{item.requirement}</strong>
              {IMPORTANCE[item.importance] ?? ''}
              <span className="evidence">{item.evidence}</span>
            </div>
          </li>
        ))}
      </ul>
      <p className="muted small">
        Scored {fit.scored} by {fit.model}. The core of the role counts double a must-have,
        which counts double a nice-to-have.
      </p>
    </section>
  )
}
