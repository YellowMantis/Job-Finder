import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ApiError, api } from '../api/client'
import type { BatchRecord, ConnectionsAnswer, FitProgress, Job } from '../api/types'
import type { Estimate } from '../logic/scoring'
import { Dropdown } from './Dropdown'
import { RollingNumber } from './RollingNumber'
import {
  SESSION_HOURS, batchesLabel, dayOf, estimate, formatDuration, formatTokens, runProgress,
  sessionPercent, tokensOf, totalsFor, totalsSince,
} from '../logic/scoring'

type Props = {
  candidates: Job[] // jobs in the table below that can be scored, in its order
  shownCount: number // all jobs in the table below
  progress: FitProgress | null
  log: BatchRecord[]
  providerName: string // e.g. "Claude Code"
  connections: ConnectionsAnswer | null // to switch AI from here
  onSwitch: (connectionId: string) => void
  onManage: () => void // open Settings, AI connections
  onCalibrated: (answer: ConnectionsAnswer) => void
  batchSize: number
  onStart: (jobs: Job[]) => void
  onStop: () => void
}

// Choose how many jobs to score, see what that will probably use, and follow
// the run. The right half of the bar beside your CV: scores belong to that CV.
export function ScoringPanel(props: Props) {
  const {
    candidates, shownCount, progress, log, providerName, connections, batchSize,
    onStart, onStop, onSwitch, onManage, onCalibrated,
  } = props
  const active = connections?.connections.find((c) => c.id === connections.active)
  const perThousand = active?.calibration?.percent_per_1k_tokens
  const [wanted, setWanted] = useState(batchSize) // how many you asked for
  // Today's date, worked out once when the panel appears (drawing must give
  // the same result every time, so the clock isn't read while drawing).
  const [day] = useState(() => dayOf(new Date()))
  const [sessionStart] = useState(() => Date.now() - SESSION_HOURS * 3600 * 1000)
  const session = totalsSince(sessionStart, log)

  const available = candidates.length
  const count = Math.max(1, Math.min(wanted, available)) // never more than there are
  const guess = estimate(log, count)
  const last = log.at(-1)
  const today = totalsFor(day, log)

  return (
    <div className="score-part">
      <span className="score-count" title={available === 0
        ? 'Every job in the table with posting text already has a score for this CV. ' +
          'Change the filters to see others.'
        : 'Jobs in the table below with posting text and no score for this CV yet. ' + ORDER_NOTE}>
        <span className="status-dot" aria-hidden="true" />
        {available === 0
          ? <>All <strong>{shownCount}</strong> scored</>
          : <><strong><RollingNumber value={available} /></strong> to score</>}
      </span>
      <Dropdown className="field" value={connections?.active ?? ''} disabled={progress?.running}
        label="Score with" title="The AI that scores"
        options={(connections?.connections ?? []).map((c) => ({ value: c.id, label: c.name }))}
        onChange={(id) => { if (id !== connections?.active) onSwitch(id) }} />

      {progress?.running ? (
        <>
          <RunProgress progress={progress} expected={estimate(log, progress.total)?.seconds ?? null} />
          <button className="button secondary" onClick={onStop} disabled={progress.stop_requested}>
            {progress.stop_requested ? 'Stopping after this batch…' : 'Stop after this batch'}
          </button>
        </>
      ) : available > 0 && (
        // The two Score buttons stay together on one line, even when the bar wraps.
        <span className="score-buttons">
          {/* How many, joined to the button that scores them. Each button carries
              its time; the full estimate is in Details and on hover. */}
          <span className="score-group">
            <input type="number" className="count-input" min={1} max={available} value={count}
              aria-label="How many jobs to score" title="How many jobs to score, from the top of the table"
              onChange={(event) => setWanted(Number(event.target.value) || 1)} />
            <button className="button score-button" onClick={() => onStart(candidates.slice(0, count))}
              title={`${costLine(count, batchSize, guess, perThousand)}. ${ESTIMATE_NOTE}`}>
              <SparkIcon />
              Score {count} {count === 1 ? 'job' : 'jobs'}
              <span className="score-cost">{shortCost(guess)}</span>
            </button>
          </span>
          {count < available && (
            <button className="button secondary score-button" onClick={() => onStart(candidates)}
              title={`${costLine(available, batchSize, estimate(log, available), perThousand)}. ${ESTIMATE_NOTE}`}>
              Score all {available}
              <span className="score-cost">{shortCost(estimate(log, available))}</span>
            </button>
          )}
        </span>
      )}

      {/* Short labelled rows: what scoring will probably use, then what it has used. */}
      <ScoringDetails>
        {available > 0 && !progress?.running && (
          <section>
            <h4 title={ESTIMATE_NOTE}>Estimate <span>from your past batches</span></h4>
            <dl className="detail-rows">
              <dt>Score {count}</dt><dd>{costLine(count, batchSize, guess, perThousand)}</dd>
              {count < available && <>
                <dt>Score all {available}</dt>
                <dd>{costLine(available, batchSize, estimate(log, available), perThousand)}</dd>
              </>}
            </dl>
          </section>
        )}
        <section>
          <h4>Usage</h4>
          <dl className="detail-rows">
            <dt>Last batch</dt>
            <dd>{last
              ? <>{jobsWord(last.jobs)} · {formatTokens(tokensOf(last))} tokens
                {last.seconds !== undefined && ` · ${formatDuration(last.seconds)}`}</>
              : 'none yet'}</dd>
            <dt>Today</dt>
            <dd title={today.costUsd > 0 ? 'What it would cost paid per use. On a subscription it ' +
              'counts towards your usage limits instead.' : undefined}>
              {jobsWord(today.jobs)} · {formatTokens(today.tokens)} tokens
              {today.costUsd > 0 && ` · ≈ $${today.costUsd.toFixed(2)} at API prices`}
            </dd>
            {active?.kind === 'claude' && (
              <SessionUsage tokens={session.tokens} jobs={session.jobs} perThousand={perThousand}
                connectionId={active.id} onCalibrated={onCalibrated} />
            )}
          </dl>
          {/* Gemini reports the tokens each answer used, but not what is left of
              your free quota: only your Google account shows that. A plain link,
              opened in your browser; the app sends nothing to it. */}
          {active?.kind === 'api' && active.service === 'gemini' && (
            <p>
              Your free quota left:{' '}
              <a href="https://aistudio.google.com/rate-limit" target="_blank" rel="noopener noreferrer">
                Google AI Studio
              </a>
            </p>
          )}
        </section>
        <p className="detail-foot">
          <span title={ORDER_NOTE}>Scored from the top of the table: sort it to choose which.</span>
          <span>{providerName} · <button className="link-button" onClick={onManage}>Manage</button></span>
        </p>
      </ScoringDetails>
    </div>
  )
}

const ORDER_NOTE = 'Jobs are scored from the top of the table down. Sorted by Fit, the unscored ' +
  'ones come in order of fewest years asked, then newest. To choose differently, sort the ' +
  'table by another column first, such as Distance.'

// "Details ▾": usage and the AI connection, in a small box that opens under
// the button. A click anywhere else, or Esc, closes it.
function ScoringDetails({ children }: { children: ReactNode }) {
  const box = useRef<HTMLDetailsElement>(null)
  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (box.current?.open && !box.current.contains(event.target as Node)) box.current.open = false
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape' && box.current) box.current.open = false
    }
    document.addEventListener('mousedown', closeOutside)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeOutside)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])
  return (
    <details ref={box} className="score-details">
      <summary>Details</summary>
      <div className="score-details-box">{children}</div>
    </details>
  )
}

// A small four-pointed star on the Score button: "the AI does this".
function SparkIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l1.9 5.6 5.6 1.9-5.6 1.9L12 18l-1.9-5.6-5.6-1.9 5.6-1.9z" />
    </svg>
  )
}

// "· ~33 s" beside a button's label, so both buttons fit on one line; the
// tokens are in Details and on hover. Nothing before the first timed batch.
function shortCost(guess: Estimate | null) {
  return guess?.seconds != null ? `· ~${formatDuration(guess.seconds)}` : ''
}

const ESTIMATE_NOTE = 'Estimated from your past batches. You can stop after any batch.'

// "2 batches · ≈ 18k tokens · ≈ 1 min", the small line inside a Score button.
// Before the first batch there is nothing to estimate from, so only the batches.
function costLine(count: number, batchSize: number, guess: Estimate | null,
  perThousand: number | undefined) {
  const parts = [batchesLabel(count, batchSize)]
  if (guess) {
    parts.push(`≈ ${formatTokens(guess.tokens)} tokens`)
    if (perThousand !== undefined) parts.push(`≈ ${sessionPercent(guess.tokens, perThousand)}% of a session`)
    if (guess.seconds !== null) parts.push(`≈ ${formatDuration(guess.seconds)}`)
  }
  return parts.join(' · ')
}

// The bar and the time so far while scoring. It redraws every second, and
// only exists while a run is going.
function RunProgress({ progress, expected }: { progress: FitProgress; expected: number | null }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const { done, total, started } = progress
  if (!total) return <span className="progress">Preparing…</span>
  const elapsed = started ? Math.max(0, Math.round(now / 1000 - started)) : 0
  const { share, secondsLeft } = runProgress(done, total, elapsed, expected)
  return (
    <span className="run-progress">
      {/* With no value, the bar shows that it's working without a share. */}
      <progress max={1} value={share ?? undefined} />
      <span className="progress">
        Scoring {total} {total === 1 ? 'job' : 'jobs'}{done > 0 && `: ${done} done`}
        {' '}· {formatDuration(elapsed)} so far
        {secondsLeft !== null && `, about ${formatDuration(secondsLeft)} left`}
      </span>
    </span>
  )
}

// A Claude plan has an allowance that resets every 5 hours, shown as a % by
// Claude Code's /usage. Programs can't read that %, so you can type it once:
// the app then learns what its batches cost as a share of your session.
function SessionUsage({ tokens, jobs, perThousand, connectionId, onCalibrated }: {
  tokens: number
  jobs: number
  perThousand: number | undefined
  connectionId: string
  onCalibrated: (answer: ConnectionsAnswer) => void
}) {
  const [percent, setPercent] = useState('')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState('')

  async function save() {
    setError('')
    try {
      onCalibrated(await api.calibrate(connectionId, Number(percent)))
      setOpen(false)
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Not saved.')
    }
  }

  // A row of the Usage list; measuring opens a small form under it.
  return (
    <>
      <dt title="A Claude session: the allowance that resets every 5 hours">Last {SESSION_HOURS} hours</dt>
      <dd>
        {jobsWord(jobs)} · {formatTokens(tokens)} tokens
        {perThousand !== undefined && ` · ≈ ${sessionPercent(tokens, perThousand)}% of your session`}
        {' · '}
        <button className="link-button" onClick={() => setOpen(!open)}
          title="Tell Veri the % that Claude Code's /usage shows, so it can estimate in %">
          {perThousand === undefined ? 'Show as %' : 'Measure again'}
        </button>
      </dd>
      {open && (
        <dd className="calibrate">
          <label>
            "Current session" % from <code>/usage</code> in Claude Code:{' '}
            <input type="number" min={1} max={100} value={percent}
              onChange={(event) => setPercent(event.target.value)} />%
          </label>
          <button className="button secondary" onClick={save} disabled={!percent}>Save</button>
          <span className="muted">It counts all your Claude use, so estimates lean high.</span>
          {error && <span className="error-text">{error}</span>}
        </dd>
      )}
    </>
  )
}

// "1 job", "10 jobs".
function jobsWord(count: number) {
  return `${count} ${count === 1 ? 'job' : 'jobs'}`
}
