import { useEffect, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { BatchRecord, ConnectionsAnswer, FitProgress, Job } from '../api/types'
import {
  SESSION_HOURS, batchesLabel, dayOf, estimate, formatDuration, formatTokens, runProgress,
  sessionPercent, tokensOf, totalsFor, totalsSince,
} from '../logic/scoring'

type Props = {
  candidates: Job[] // jobs in the table below that can be scored, in table order
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
// the run. Sits under the CV box: scores belong to the CV you loaded.
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
    <section className="scoring">
      <p className="scoring-status">
        <strong>Fit scores</strong>{' '}
        {available === 0
          ? `Nothing to score among the ${shownCount} jobs in the table below: every one with ` +
            'posting text already has a score for this CV. Change the filters to see others.'
          : `${available} of the ${shownCount} jobs in the table below can be scored ` +
            '(they have posting text and no score for this CV). The top rows are scored first.'}
      </p>

      {progress?.running ? (
        <div className="scoring-actions">
          <RunProgress progress={progress} expected={estimate(log, progress.total)?.seconds ?? null} />
          <button className="button secondary" onClick={onStop} disabled={progress.stop_requested}>
            {progress.stop_requested ? 'Stopping after this batch…' : 'Stop after this batch'}
          </button>
        </div>
      ) : available > 0 && (
        <div className="scoring-actions">
          <label>
            Score{' '}
            <input type="number" className="count-input" min={1} max={available} value={count}
              onChange={(event) => setWanted(Number(event.target.value) || 1)} />
            {' '}jobs
          </label>
          <button className="button" onClick={() => onStart(candidates.slice(0, count))}>
            Score {count} ({batchesLabel(count, batchSize)})
          </button>
          {count < available && (
            <button className="button secondary" onClick={() => onStart(candidates)}>
              Score all {available} ({batchesLabel(available, batchSize)})
            </button>
          )}
          {guess && (
            <span className="muted">
              ≈ {formatTokens(guess.tokens)} tokens
              {perThousand !== undefined && ` (≈ ${sessionPercent(guess.tokens, perThousand)}% of a session)`}
              {guess.seconds !== null && `, ≈ ${formatDuration(guess.seconds)}`}, judging by
              your past batches
            </span>
          )}
        </div>
      )}

      <div className="scoring-with">
        <label>
          Score with{' '}
          <select value={connections?.active ?? ''} disabled={progress?.running}
            onChange={(event) => onSwitch(event.target.value)}>
            {(connections?.connections ?? []).map((connection) => (
              <option key={connection.id} value={connection.id}>{connection.name}</option>
            ))}
          </select>
        </label>
        <button className="link-button" onClick={onManage}>Manage AI connections</button>
      </div>

      <p className="scoring-usage muted small">
        Scored by {providerName}.{' '}
        {last
          ? <>Last batch: {last.jobs} jobs · {formatTokens(tokensOf(last))} tokens
            {last.seconds !== undefined && ` · ${formatDuration(last.seconds)}`} · {last.time}. </>
          : 'No batches scored yet. '}
        Today: {today.batches} batch(es), {today.jobs} jobs, {formatTokens(today.tokens)} tokens
        {today.costUsd > 0 &&
          ` (≈ $${today.costUsd.toFixed(2)} if paid per use; on a subscription it counts towards ` +
          'its usage limits instead, which Claude Code shows with /usage)'}
        . You can stop after any batch.
      </p>
      {active?.kind === 'claude' && (
        <SessionUsage tokens={session.tokens} jobs={session.jobs} perThousand={perThousand}
          connectionId={active.id} onCalibrated={onCalibrated} />
      )}
    </section>
  )
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

  return (
    <div className="session-usage muted small">
      Last {SESSION_HOURS} hours (a Claude session): {jobs} jobs, {formatTokens(tokens)} tokens
      {perThousand !== undefined && ` ≈ ${sessionPercent(tokens, perThousand)}% of your session`}.{' '}
      {!open ? (
        <button className="link-button" onClick={() => setOpen(true)}>
          {perThousand === undefined ? 'Estimate it as a %' : 'Measure again'}
        </button>
      ) : (
        <span className="calibrate">
          Type the "Current session" % that <code>/usage</code> shows in Claude Code now:
          <input type="number" min={1} max={100} value={percent}
            onChange={(event) => setPercent(event.target.value)} />%
          <button className="button secondary" onClick={save} disabled={!percent}>Save</button>
          <span>It includes anything else you did with Claude, so estimates lean high.</span>
          {error && <span className="error-text">{error}</span>}
        </span>
      )}
    </div>
  )
}
