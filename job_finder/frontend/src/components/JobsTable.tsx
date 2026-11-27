import { useMemo, useRef, type MouseEvent } from 'react'
import type { Job } from '../api/types'
import { useRowGlide } from '../hooks/useRowGlide'
import {
  ageInDays, ageLabelCapital, distanceText, fieldLabel, modeOf, placeOf, placeSource, webLink, yearsText, type Sort, type SortKey,
} from '../logic/jobs'
import { scoreState, type ScoringRun } from '../logic/scoring'
import { FitBadge } from './FitBadge'

type Props = {
  jobs: Job[] // already filtered and sorted
  run: ScoringRun // the latest scoring run's jobs, to show which are waiting and which just arrived
  running: boolean // that run is still going
  sort: Sort
  onSort: (key: SortKey) => void
  lastOpened: string | null // the job opened last, marked until another is opened
  onOpen: (job: Job) => void
  onApplied: (job: Job, applied: boolean) => void
}

// Short values are centred under their heading; text reads best from the left.
const COLUMNS: { key: SortKey | null; label: string; centred?: boolean; hint?: string }[] = [
  { key: 'fit', label: 'Fit', centred: true },
  { key: 'title', label: 'Position & company' },
  { key: 'field', label: 'Field' },
  { key: 'years', label: 'Years', centred: true },
  { key: 'place', label: 'Location' },
  { key: 'distance', label: 'Distance', centred: true },
  { key: 'mode', label: 'Work mode', centred: true },
  { key: 'age', label: 'Posted', centred: true,
    hint: 'When the job was first posted. A repost on LinkedIn keeps this date, so an older job may still be hiring.' },
  { key: null, label: '', centred: true }, // Apply
  { key: 'applied', label: 'Applied', centred: true },
]

// The positions table. It only displays: the rows, the order and what happens
// on a click all come from App, through the props above.
export function JobsTable({ jobs, run, running, sort, onSort, lastOpened, onOpen, onApplied }: Props) {
  // Rows glide to their new place when new data (scores) re-orders the same
  // rows; a new sort or filter (a different `order` key) just redraws.
  const body = useRef<HTMLTableSectionElement>(null)
  const urls = useMemo(() => jobs.map((job) => job.url).sort().join('\n'), [jobs])
  useRowGlide(body, `${sort.key} ${sort.descending}\n${urls}`)

  return (
    <div className="table-wrap">
      <table className="jobs-table">
        <thead>
          <tr>
            {COLUMNS.map(({ key, label, centred, hint }) => {
              const sorted = key !== null && key === sort.key
              const classes = [centred && 'centred', key && 'sortable',
                sorted && 'sorted', sorted && sort.descending && 'descending']
              return (
                <th key={label || 'apply'} className={classes.filter(Boolean).join(' ')} title={hint}
                  onClick={key ? () => onSort(key) : undefined}>
                  {label}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody ref={body}>
          {jobs.map((job) => (
            <JobRow key={job.url} job={job} scoring={scoreState(job, run, running)}
              opened={job.url === lastOpened} onOpen={onOpen} onApplied={onApplied} />
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && <p className="empty">No positions match these filters.</p>}
    </div>
  )
}

type RowProps = Pick<Props, 'onOpen' | 'onApplied'> & {
  job: Job
  opened: boolean
  scoring: 'waiting' | 'new' | null
}

function JobRow({ job, opened, scoring, onOpen, onApplied }: RowProps) {
  const mode = modeOf(job)
  // Clicks on the link and the tick box must not also open the side panel.
  const stop = (event: MouseEvent) => event.stopPropagation()

  return (
    <tr className={[job.applied && 'is-applied', opened && 'last-opened'].filter(Boolean).join(' ') || undefined}
      data-url={job.url} onClick={() => onOpen(job)}>
      <td className="centred"><FitBadge job={job} state={scoring} /></td>
      {/* The title, and the company under it in small grey text. */}
      <td className="wrap">
        <span className="job-title">{job.title}</span>
        {job.level === 'junior' && <> <span className="badge junior">Junior</span></>}
        {job.for_graduates && (
          <> <span className="badge graduates" title="The posting is aimed at recent graduates">Graduates</span></>
        )}
        <div className="job-company">{job.company}</div>
      </td>
      <td title={job.field_reason && `Sorted here because the ${job.field_reason}`}>{fieldLabel(job.field)}</td>
      <td className={job.years === null ? 'centred muted' : 'centred'}
        title={job.years === null ? "The posting doesn't say, or we don't have its text"
          : 'Years of experience the posting asks for'}>
        {yearsText(job)}
      </td>
      {/* Hovering says where the place comes from: the company's own site, or
          only the listing, which often names the company's main office. */}
      <td className="wrap-narrow" title={placeSource(job)}>{placeOf(job)}</td>
      <td className="centred" title={placeSource(job)}>{distanceText(job)}</td>
      <td className="centred">
        {/* hybrid, remote, on-site: a coloured tag; otherwise "Not stated" in
            quiet grey, the same words as in the Work mode filter */}
        {mode && mode !== 'not stated'
          ? <span className={`mode-tag ${mode}`}>{mode[0].toUpperCase() + mode.slice(1)}</span>
          : <span className="muted small" title="Neither the listing nor the posting says">Not stated</span>}
      </td>
      <td className="centred muted">{ageLabelCapital(ageInDays(job))}</td>
      <td className="centred">
        <a className="apply-chip" href={webLink(job.apply_url)} target="_blank" rel="noopener noreferrer"
          onClick={stop} title="Opens the employer's posting in your browser">Apply ↗</a>
      </td>
      {/* Only the box itself ticks (not a <label>, which would make the whole
          cell a target), and a click beside it doesn't open the job either.
          The date you applied is in the Applied tab, not here. */}
      <td className="centred applied-cell" onClick={stop}>
        <span className="applied">
          <AppliedTick checked={Boolean(job.applied)} onChange={(checked) => onApplied(job, checked)} />
        </span>
      </td>
    </tr>
  )
}

// The Applied box: a real checkbox (keyboard and screen readers work as
// usual), drawn by index.css: it fills green and its tick draws itself like a
// pen stroke; unticking runs the stroke back.
function AppliedTick({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <span className="tick">
      <input type="checkbox" checked={checked} aria-label="Applied"
        onChange={(event) => onChange(event.target.checked)} />
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" /></svg>
    </span>
  )
}
