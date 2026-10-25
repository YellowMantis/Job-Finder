import { useCallback, useEffect, useMemo, useState } from 'react'
import { ApiError, api } from './api/client'
import type {
  BatchRecord, ConnectionsAnswer, FitProgress, Job, JobsAnswer, Preferences, PreferencesAnswer,
  Status, UpdateProgress,
} from './api/types'
import { ConnectionsSettings } from './components/ConnectionsSettings'
import { CvDropZone } from './components/CvDropZone'
import { FilterBar } from './components/FilterBar'
import { HiddenJobs } from './components/HiddenJobs'
import { JobPanel } from './components/JobPanel'
import { JobsTable } from './components/JobsTable'
import { SkillGaps } from './components/SkillGaps'
import { PreferencesForm } from './components/PreferencesForm'
import { SetupWizard } from './components/SetupWizard'
import { UpdateBanner } from './components/UpdateBanner'
import { ScoringPanel } from './components/ScoringPanel'
import { useProgress } from './hooks/useProgress'
import {
  passesFilters, sortJobs, startingFilters, type Filters, type Sort, type SortKey,
} from './logic/jobs'
import { scorable } from './logic/scoring'

type Message = { text: string; isError: boolean } | null

// Everything the page shows comes from these two requests.
const fetchData = () => Promise.all([api.status(), api.jobs()])

// The whole page. App holds the state (the data and your choices) and passes
// it down to the components, which only display it and report clicks back.
function App() {
  const [status, setStatus] = useState<Status | null>(null)
  const [jobs, setJobs] = useState<Job[]>([])
  const [hiddenCount, setHiddenCount] = useState(0)
  const [dataVersion, setDataVersion] = useState(0) // goes up whenever the data is reloaded
  const [filters, setFilters] = useState<Filters | null>(null) // set once status arrives
  const [sort, setSort] = useState<Sort>({ key: 'fit', descending: true })
  const [tab, setTab] = useState<'jobs' | 'skills' | 'hidden'>('jobs')
  const [openUrl, setOpenUrl] = useState<string | null>(null) // the job in the side panel
  const [error, setError] = useState('') // the page can't work at all
  const [message, setMessage] = useState<Message>(null) // news or a problem, page still works
  const [log, setLog] = useState<BatchRecord[]>([]) // recent scoring batches
  const [connections, setConnections] = useState<ConnectionsAnswer | null>(null)
  const [view, setView] = useState<'jobs' | 'settings'>('jobs')
  const [preferences, setPreferences] = useState<PreferencesAnswer | null>(null)

  // Show freshly loaded data. Filters are set only the first time, from your
  // preferences; after that your own choices are kept.
  const showData = useCallback(([status, answer]: [Status, JobsAnswer]) => {
    setStatus(status)
    setJobs(answer.jobs)
    setHiddenCount(answer.hidden_count)
    setDataVersion((version) => version + 1)
    setFilters((current) => current ?? startingFilters(status.default_fields, status.default_max_km))
  }, [])

  useEffect(() => {
    fetchData().then(showData).catch(() =>
      setError('The back end is not running. Start it with: python job_finder/app.py'))
    api.fitLog().then(setLog).catch(() => {})
    api.connections().then(setConnections).catch(() => {})
    api.preferences().then(setPreferences).catch(() => {})
    // The check for a newer version runs in the background when the app starts,
    // and may answer after the page's first look: look once more a little later.
    const recheck = setTimeout(() => api.status().then(setStatus).catch(() => {}), 8000)
    return () => clearTimeout(recheck)
  }, [showData])

  // New preferences change what is hidden and every distance: reload the
  // table, and tick your new fields in the Fields filter.
  function preferencesSaved(saved: Preferences) {
    setPreferences((current) => current && { ...current, preferences: saved })
    setFilters((current) => current && { ...current, fields: saved.fields })
    fetchData().then(showData).catch(() => {})
  }

  // After any change to the AI connections: the list, and the status (which
  // says which one scores) are fetched again.
  function connectionsChanged(answer: ConnectionsAnswer) {
    setConnections(answer)
    api.status().then(setStatus).catch(() => {})
  }

  async function switchConnection(connectionId: string) {
    try {
      connectionsChanged(await api.useConnection(connectionId))
    } catch (problem) {
      setMessage({ text: problem instanceof ApiError ? problem.message : 'Could not switch.', isError: true })
    }
  }

  // Scoring: after each finished batch, show the new scores and what the batch
  // used; when it stops, say how it went.
  const fit = useProgress(api.fitStatus, useCallback((progress: FitProgress) => {
    fetchData().then(showData).catch(() => {})
    api.fitLog().then(setLog).catch(() => {})
    if (progress.running) return
    setMessage(progress.error
      ? { text: progress.error, isError: true }
      : { text: `Scored ${progress.done} position(s).`, isError: false })
  }, [showData]))

  // Updating the listings: reload once it has finished.
  const update = useProgress(api.updateStatus, useCallback((progress: UpdateProgress) => {
    if (progress.running) return
    if (progress.error) return setMessage({ text: progress.error, isError: true })
    fetchData().then(showData).catch(() => {})
    const s = progress.summary
    if (s) {
      setMessage({
        text: `Updated: ${s.jobs} positions shown, ${s.hidden} hidden by your preferences, ` +
          `${s.new_postings} posting text(s) fetched.`,
        isError: false,
      })
    }
  }, [showData]))

  // The rows to show. useMemo redoes this only when the jobs, filters or
  // order change, not on every redraw (for example when the panel opens).
  const newSince = status?.new_since ?? null // jobs that appeared after this are new
  const shown = useMemo(
    () => (filters ? sortJobs(jobs.filter((job) => passesFilters(job, filters, newSince)), sort) : []),
    [jobs, filters, sort, newSince])

  // Clicking the sorted column again reverses it; fit starts best first.
  function changeSort(key: SortKey) {
    setSort((current) => ({
      key,
      descending: current.key === key ? !current.descending : key === 'fit',
    }))
  }

  // "Applied" changes on screen at once (an optimistic update), then shows the
  // date the back end saved. If saving fails, the tick goes back and says why.
  async function markApplied(job: Job, applied: boolean) {
    const setFor = (value: string | null) =>
      setJobs((all) => all.map((j) => (j.url === job.url ? { ...j, applied: value } : j)))
    setFor(applied ? new Date().toISOString().slice(0, 10) : null)
    try {
      setFor((await api.setApplied(job.url, applied)).applied)
    } catch {
      setFor(job.applied)
      setMessage({ text: 'Could not save "applied". Is the back end running?', isError: true })
    }
  }

  // A new CV: scores made for the previous one no longer apply, so reload.
  async function uploadCv(file: File) {
    try {
      await api.uploadCv(file)
      showData(await fetchData())
      setMessage({ text: 'CV saved. Score the shown jobs to see how they fit it.', isError: false })
    } catch (problem) {
      const text = problem instanceof ApiError ? problem.message : 'The CV could not be uploaded.'
      setMessage({ text, isError: true })
    }
  }

  async function saveYears(years: number) {
    try {
      const cv = await api.setYears(years)
      setStatus((current) => current && { ...current, cv })
      setMessage({ text: `Saved: ${years} year(s) of paid work. New scores will use it.`, isError: false })
    } catch (problem) {
      setMessage({ text: problem instanceof ApiError ? problem.message : 'Not saved.', isError: true })
    }
  }

  async function startScoring(jobs: Job[], again = false) {
    // Scoring uses your AI's allowance (or your PC's time), so ask first.
    const scorer = status?.scorer
    if (!scorer) return
    const requests = Math.ceil(jobs.length / scorer.batch_size)
    const ok = window.confirm(`Score ${jobs.length} job(s) with ${scorer.name}?\n\n` +
      `That is ${requests} request(s) of up to ${scorer.batch_size} jobs. It counts towards ` +
      "that service's usage limits (none for a model on this PC). You can stop after any batch.")
    if (!ok) return
    try {
      await api.startFit(jobs.map((job) => job.url), again)
      setMessage({ text: `Scoring ${jobs.length} job(s). Scores appear as each batch finishes.`, isError: false })
      await fit.check()
    } catch (problem) {
      setMessage({ text: problem instanceof ApiError ? problem.message : 'Scoring did not start.', isError: true })
    }
  }

  async function startUpdate() {
    await api.startUpdate()
    await update.check()
  }

  // The first-run setup is done: preferences are saved, so download the jobs.
  function setupFinished(saved: Preferences) {
    preferencesSaved(saved)
    setView('jobs')
    startUpdate().catch(() => {})
  }

  // The open job is looked up by its link, so it always shows the latest data
  // (a new score, or a tick on Applied) rather than a copy from when it opened.
  const openJob = jobs.find((job) => job.url === openUrl) ?? null
  // useCallback keeps the same function between redraws, so the panel's Esc
  // listener isn't removed and added again every time.
  const closePanel = useCallback(() => setOpenUrl(null), [])

  if (error) return <main><p className="message error">{error}</p></main>
  if (status?.startup_problem) return <main><p className="message error">{status.startup_problem}</p></main>
  if (!status || !filters) return <main><p className="muted">Loading…</p></main>

  return (
    <>
      <header className="top">
        <div>
          <h1>Job Finder</h1>
          <p className="subtitle">
            {status.setup_needed ? 'Set up in three short steps' : <>Positions across Israel · {status.home ? `distances from ${status.home}` : 'no home chosen: set it in Settings'}</>}
            {!status.setup_needed &&
              (status.jobs_updated ? ` · listings updated ${status.jobs_updated}` : ' · no listings yet')}
          </p>
        </div>
        {/* Hidden during the first-run setup, so it is finished before anything else. */}
        {!status.setup_needed && <div className="actions">
          <button className="button secondary" onClick={() => setView(view === 'jobs' ? 'settings' : 'jobs')}>
            {view === 'jobs' ? 'Settings' : '← Back to positions'}
          </button>
          {update.progress?.running && (
            <span className="progress">
              {update.progress.stage}
              {update.progress.total ? ` ${update.progress.done} of ${update.progress.total}…` : '…'}
            </span>
          )}
          <button className="button secondary" onClick={startUpdate}
            disabled={update.progress?.running}>
            {update.progress?.running ? 'Updating…' : 'Update listings'}
          </button>
        </div>}
      </header>
      {status.update && !status.setup_needed && (
        <UpdateBanner current={status.version} update={status.update} />
      )}
      {status.setup_needed && connections && preferences ? (
        <SetupWizard connections={connections} preferences={preferences} cv={status.cv}
          scorer={status.scorer} onConnections={connectionsChanged}
          onCv={() => api.status().then(setStatus).catch(() => {})}
          onFinished={setupFinished} />
      ) : view === 'settings' ? (
        <main className="settings">
          {preferences && <PreferencesForm answer={preferences} onSaved={preferencesSaved} />}
          {connections && <ConnectionsSettings info={connections} onChange={connectionsChanged} />}
        </main>
      ) : (
      <main>
        <CvDropZone cv={status.cv} onUpload={uploadCv} onYears={saveYears} />
        {message && <p className={`message${message.isError ? ' error' : ''}`}>{message.text}</p>}
        {status.cv && status.scorer && (
          <ScoringPanel candidates={scorable(shown)} shownCount={shown.length}
            progress={fit.progress} providerName={status.scorer.name}
            // Only this connection's batches: another AI's would distort the estimate.
            log={log.filter((batch) => batch.connection === status.scorer!.id)}
            batchSize={status.scorer.batch_size} onStart={startScoring}
            onStop={() => api.stopFit().then(fit.check).catch(() => {})}
            connections={connections} onSwitch={switchConnection}
            onManage={() => setView('settings')} onCalibrated={connectionsChanged} />
        )}
        {status.cv && !status.scorer && (
          <section className="scoring">
            <p className="scoring-status">
              <strong>Fit scores</strong> To score jobs against your CV, add an AI connection
              first: Claude Code, a service with your key, or a model on this PC.{' '}
              <button className="link-button" onClick={() => setView('settings')}>Open Settings</button>
            </p>
          </section>
        )}

        <nav className="tabs">
          <button className={`tab${tab === 'jobs' ? ' active' : ''}`} onClick={() => setTab('jobs')}>
            Positions <span className="count">{shown.length}</span>
          </button>
          <button className={`tab${tab === 'skills' ? ' active' : ''}`} onClick={() => setTab('skills')}>
            What to learn
          </button>
          <button className={`tab${tab === 'hidden' ? ' active' : ''}`} onClick={() => setTab('hidden')}>
            Hidden <span className="count">{hiddenCount}</span>
          </button>
        </nav>

        {tab !== 'hidden' ? (
          <>
            {/* The same filters for both tabs: the skills are those of the jobs in the table. */}
            <FilterBar jobs={jobs} filters={filters} onChange={setFilters} />
            {tab === 'jobs' ? (
              <JobsTable jobs={shown} newSince={newSince} sort={sort} onSort={changeSort}
                onOpen={(job) => setOpenUrl(job.url)} onApplied={markApplied} />
            ) : (
              <SkillGaps jobs={shown} onOpen={(job) => setOpenUrl(job.url)} />
            )}
          </>
        ) : (
          // Rendered (and so fetched) only while this tab is open. The key makes
          // it fetch again after the data reloads, e.g. after a new CV.
          <HiddenJobs key={dataVersion} />
        )}
        <footer className="credit">
          Job Finder {status.version} · {status.credit} · Fit scored by {status.scorer?.name ?? 'no AI yet'}
        </footer>
      </main>
      )}
      {openJob && (
        <JobPanel job={openJob} onClose={closePanel} scoring={fit.progress?.running ?? false}
          onScore={status.cv && status.scorer
            ? (again) => startScoring([openJob], again) : undefined} />
      )}
    </>
  )
}

export default App
