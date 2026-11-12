import type { MouseEvent } from 'react'
import type { Job } from '../api/types'
import {
  ageInDays, ageLabel, distanceText, isNew, modeOf, placeOf, yearsText, type Sort, type SortKey,
} from '../logic/jobs'
import { ChanceBadge } from './ChanceBadge'
import { FitBadge } from './FitBadge'

type Props = {
  jobs: Job[] // already filtered and sorted
  newSince: string | null // jobs that appeared after this get a "New" badge
  sort: Sort
  onSort: (key: SortKey) => void
  lastOpened: string | null // the job opened last, marked until another is opened
  onOpen: (job: Job) => void
  onApplied: (job: Job, applied: boolean) => void
}

// Short values are centred under their heading; text reads best from the left.
const COLUMNS: { key: SortKey | null; label: string; centred?: boolean; hint?: string }[] = [
  { key: 'fit', label: 'Fit', centred: true },
  { key: 'chance', label: 'Chance', centred: true,
    hint: 'How realistic it is as a first job: years asked, level, kind of role and fit. Hover a badge for why.' },
  { key: 'title', label: 'Position' },
  { key: 'company', label: 'Company' },
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
export function JobsTable({ jobs, newSince, sort, onSort, lastOpened, onOpen, onApplied }: Props) {
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
        <tbody>
          {jobs.map((job) => (
            <JobRow key={job.url} job={job} isNew={isNew(job, newSince)}
              opened={job.url === lastOpened} onOpen={onOpen} onApplied={onApplied} />
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && <p className="empty">No positions match these filters.</p>}
    </div>
  )
}

type RowProps = Pick<Props, 'onOpen' | 'onApplied'> & { job: Job; isNew: boolean; opened: boolean }

function JobRow({ job, isNew, opened, onOpen, onApplied }: RowProps) {
  const mode = modeOf(job)
  // Clicks on the link and the tick box must not also open the side panel.
  const stop = (event: MouseEvent) => event.stopPropagation()

  return (
    <tr className={[job.applied && 'is-applied', opened && 'last-opened'].filter(Boolean).join(' ') || undefined}
      onClick={() => onOpen(job)}>
      <td className="centred"><FitBadge job={job} /></td>
      <td className="centred"><ChanceBadge job={job} /></td>
      <td className="wrap">
        {job.title}
        {job.level === 'junior' && <> <span className="badge junior">Junior</span></>}
        {isNew && <> <span className="badge new">New</span></>}
        {job.for_graduates && (
          <> <span className="badge graduates" title="The posting is aimed at recent graduates">Graduates</span></>
        )}
      </td>
      <td className="wrap-narrow">{job.company}</td>
      <td>{job.field}</td>
      <td className={job.years === null ? 'centred muted' : 'centred'}
        title={job.years === null ? "The posting doesn't say, or we don't have its text"
          : 'Years of experience the posting asks for'}>
        {yearsText(job)}
      </td>
      <td className="wrap-narrow">{placeOf(job)}</td>
      <td className="centred">{distanceText(job)}</td>
      <td className={mode && mode !== 'not stated' ? 'centred' : 'centred muted'}>{mode || '–'}</td>
      <td className="centred muted">{ageLabel(ageInDays(job))}</td>
      <td className="centred">
        <a className="apply-chip" href={job.apply_url} target="_blank" rel="noopener noreferrer"
          onClick={stop}>Apply</a>
      </td>
      {/* Only the box itself ticks (not a <label>, which would make the whole
          cell a target), and a click beside it doesn't open the job either. */}
      <td className="centred applied-cell" onClick={stop}>
        <span className="applied">
          <input type="checkbox" checked={Boolean(job.applied)} aria-label="Applied"
            onChange={(event) => onApplied(job, event.target.checked)} />
          {job.applied && ` ${job.applied}`}
        </span>
      </td>
    </tr>
  )
}
