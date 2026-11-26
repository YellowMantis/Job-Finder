import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Fit, HideReason, Job, Match } from '../api/types'
import { ageInDays, ageLabel, distanceText, fitClass, placeOf } from '../logic/jobs'
import { postingBlocks } from '../logic/posting'
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
  onApplied: (applied: boolean) => void // tick or untick "I applied"
}

// The panel that slides in when you click a position: its fit review and the
// full posting text, which is fetched now, for this one job.
export function JobPanel({ job, onClose, onScore, scoring, onHide, onUseReview, onApplied }: Props) {
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
        {/* The same mark as the table's Applied tick, without closing the panel. */}
        {job.applied ? (
          <span className="panel-applied">
            ✓ Applied {job.applied}
            <button className="link-button" onClick={() => onApplied(false)}>Undo</button>
          </span>
        ) : (
          <button className="button secondary" onClick={() => onApplied(true)}>Mark as applied</button>
        )}
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
      {!job.has_text || text === null ? (
        <p className="panel-text muted">
          {!job.has_text
            ? "The full posting text isn't available for this company yet. Open the posting to read it."
            : 'Loading the posting text…'}
        </p>
      ) : <PostingText text={text} />}
    </aside>
  )
}

const ROWS: { match: Match; label: string }[] = [
  { match: 'no', label: 'Missing' }, { match: 'partial', label: 'Partly' }, { match: 'yes', label: 'You have' },
]
const WEIGHTS = 'The core of the role counts double a must-have, which counts double a nice-to-have.'

// The score and its summary, then every requirement as a chip in one of three
// rows: missing (red), partly (amber), you have (green). Hover a chip for the
// evidence from your CV, the badge for how the score was made.
// (PostingText, the posting as a page, is at the end of this file.)
function FitReview({ fit }: { fit: Fit }) {
  return (
    <section className="fit-box">
      <div className="fit-head">
        <h3>
          {fit.score === null
            ? 'No score for'
            : (
              // The same score box as in the table, so a score always looks the same.
              <span className={`fit-score ${fitClass(fit.score)}`}
                title={[...fit.notes, WEIGHTS].join(' ')}>
                {fit.score}<small>%</small>
                <span className="fit-meter" aria-hidden="true"><span style={{ width: `${fit.score}%` }} /></span>
              </span>
            )}
          {' '}fit
        </h3>
        <span className="muted small" title={`Scored ${fit.scored} by ${fit.model}`}>
          {modelName(fit.model)} · {fit.scored.slice(0, 10)}
        </span>
      </div>
      <p>{fit.summary}</p>
      {/* A lowered score's note is on the badge; the years chip already shows why.
          Only "not scored" needs saying out loud. */}
      {fit.score === null && fit.notes.length > 0 && <p className="fit-notes">{fit.notes.join(' ')}</p>}
      <div className="chip-rows">
        {ROWS.map(({ match, label }) => {
          const items = fit.requirements.filter((item) => item.match === match)
          return items.length > 0 && (
            <div key={match} className="chip-row">
              <span className="chip-label">{label}</span>
              <div className="chips">
                {items.map((item) => (
                  <span key={item.requirement} className={`chip ${match} ${item.importance}`}
                    title={(item.importance === 'core' ? 'Core of the role. ' : '') +
                      (item.importance === 'nice' ? 'Nice to have. ' : '') +
                      (match === 'no' ? 'Not in your CV.' : `From your CV: ${item.evidence}`)}>
                    {item.requirement}
                    {item.importance === 'core' && <span className="chip-tag">core</span>}
                    {item.importance === 'nice' && <span className="chip-tag">nice to have</span>}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

// The posting as a page: its headings, bullet lists and paragraphs, read from
// the shape of its lines (logic/posting.ts). The words are the posting's own.
function PostingText({ text }: { text: string }) {
  const blocks = useMemo(() => postingBlocks(text), [text])
  return (
    <div className="panel-text posting">
      {blocks.map((block, n) =>
        block.kind === 'heading' ? <h4 key={n}>{block.text}</h4>
        : block.kind === 'list' ? <ul key={n}>{block.items.map((item, i) => <li key={i}>{item}</li>)}</ul>
        : <p key={n}>{block.text}</p>)}
    </div>
  )
}
