import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Fit, HideReason, Job, Match } from '../api/types'
import { CHANCE_LABELS, aiChance } from '../logic/chance'
import { ageInDays, ageLabel, distanceText, fitClass, placeOf } from '../logic/jobs'
import { modelName } from '../logic/scoring'

type Props = {
  job: Job
  onClose: () => void
  // Score just this job (again: it has a score; redo it, e.g. with another AI).
  // Missing when there is nothing to score with (no CV or no AI).
  onScore?: (again: boolean) => void
  scoring: boolean // a scoring run is under way
  onHide: (reason: HideReason) => void // e.g. the posting turned out to be closed
  onUseReview: (scored: string) => void // make an earlier review the current one
}

// The panel that slides in when you click a position: its fit review and the
// full posting text, which is fetched now, for this one job.
export function JobPanel({ job, onClose, onScore, scoring, onHide, onUseReview }: Props) {
  // The last text loaded, and which job it belongs to. While another job's text
  // is still arriving, the one shown doesn't match, so the panel says "Loading".
  const [loaded, setLoaded] = useState<{ url: string; text: string } | null>(null)
  const text = loaded?.url === job.url ? loaded.text : null
  // Hide asks why first: the two reasons appear beside it. Folded again for another job.
  const [hiding, setHiding] = useState<string | null>(null) // the job being asked about

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

  // Earlier reviews of this job (another model, an earlier run), fetched like
  // the text. Fetched again when the current review changes, e.g. after
  // scoring again or choosing an earlier one.
  const [earlier, setEarlier] = useState<{ url: string; reviews: Fit[] } | null>(null)
  const [opened, setOpened] = useState<string | null>(null) // the earlier review shown in full
  const reviews = earlier?.url === job.url ? earlier.reviews : []
  useEffect(() => {
    let current = true
    api.earlierReviews(job.url)
      .then((found) => current && setEarlier({ url: job.url, reviews: found }))
      .catch(() => {})
    return () => { current = false }
  }, [job.url, job.fit?.scored])
  const shown = reviews.find((review) => review.scored === opened) ?? null

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
        {hiding === job.url ? (
          <span className="hide-choices">
            Hide because it's
            <button className="button secondary" onClick={() => onHide('closed')}>Closed</button>
            <button className="button secondary" onClick={() => onHide('not interested')}>
              Not interested
            </button>
            <button className="link-button" onClick={() => setHiding(null)}>Cancel</button>
          </span>
        ) : (
          <button className="link-button" onClick={() => setHiding(job.url)}
            title="Take it out of the table. The Hidden tab can bring it back">Hide…</button>
        )}
      </div>

      {job.fit && <FitReview fit={job.fit} />}

      {reviews.length > 0 && (
        <section className="earlier-reviews">
          <h3 className="panel-heading">Also scored</h3>
          <div className="earlier-list">
            {reviews.map((review) => (
              <button key={review.scored}
                className={`button secondary${review.scored === opened ? ' chosen' : ''}`}
                onClick={() => setOpened(review.scored === opened ? null : review.scored)}>
                {modelName(review.model)}{' '}
                {review.score === null ? '?' : `${review.score}%`}
                <span className="muted small"> · {review.scored.slice(0, 10)}</span>
              </button>
            ))}
          </div>
          {shown && (
            <>
              <FitReview fit={shown} />
              <button className="button secondary" disabled={scoring}
                title={scoring ? 'Wait until scoring has finished' : undefined}
                onClick={() => { setOpened(null); onUseReview(shown.scored) }}>
                Use this one as the score
              </button>
            </>
          )}
        </section>
      )}

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
  const chance = aiChance(fit)
  return (
    <section className="fit-box">
      <h3>
        {fit.score === null
          ? 'No score for'
          : <span className={`badge fit ${fitClass(fit.score)}`}>{fit.score}%</span>}
        {' '}fit
      </h3>
      {chance && (
        <p>
          <span className={`badge chance ${chance}`}>{CHANCE_LABELS[chance]}</span>{' '}
          {fit.chance_reason}
        </p>
      )}
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
