import type { MouseEvent } from 'react'
import type { Job } from '../api/types'
import {
  ageInDays, ageLabel, distanceText, modeOf, placeOf, yearsText, type Sort, type SortKey,
} from '../logic/jobs'
import { FitBadge } from './FitBadge'

type Props = {
  jobs: Job[] // already filtered and sorted
  sort: Sort
  onSort: (key: SortKey) => void
  onOpen: (job: Job) => void
  onApplied: (job: Job, applied: boolean) => void
}

const COLUMNS: { key: SortKey | null; label: string; numeric?: boolean }[] = [
  { key: 'fit', label: 'Fit', numeric: true },
  { key: 'title', label: 'Position' },
  { key: 'company', label: 'Company' },
  { key: 'field', label: 'Field' },
  { key: 'years', label: 'Years', numeric: true },
  { key: 'place', label: 'Location' },
  { key: 'distance', label: 'Distance', numeric: true },
  { key: 'mode', label: 'Work mode' },
  { key: 'age', label: 'Updated', numeric: true },
  { key: null, label: '' }, // Apply
  { key: 'applied', label: 'Applied' },
]

// The positions table. It only displays: the rows, the order and what happens
// on a click all come from App, through the props above.
export function JobsTable({ jobs, sort, onSort, onOpen, onApplied }: Props) {
  return (
    <div className="table-wrap">
      <table className="jobs-table">
        <thead>
          <tr>
            {COLUMNS.map(({ key, label, numeric }) => {
              const sorted = key !== null && key === sort.key
              const classes = [numeric && 'num', key && 'sortable',
                sorted && 'sorted', sorted && sort.descending && 'descending']
              return (
                <th key={label || 'apply'} className={classes.filter(Boolean).join(' ')}
                  onClick={key ? () => onSort(key) : undefined}>
                  {label}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <JobRow key={job.url} job={job} onOpen={onOpen} onApplied={onApplied} />
          ))}
        </tbody>
      </table>
      {jobs.length === 0 && <p className="empty">No positions match these filters.</p>}
    </div>
  )
}

type RowProps = Pick<Props, 'onOpen' | 'onApplied'> & { job: Job }

function JobRow({ job, onOpen, onApplied }: RowProps) {
  const mode = modeOf(job)
  // Clicks on the link and the tick box must not also open the side panel.
  const stop = (event: MouseEvent) => event.stopPropagation()

  return (
    <tr className={job.applied ? 'is-applied' : undefined} onClick={() => onOpen(job)}>
      <td className="num"><FitBadge job={job} /></td>
      <td className="wrap">
        {job.title}
        {job.level === 'junior' && <> <span className="badge junior">Junior</span></>}
      </td>
      <td className="wrap-narrow">{job.company}</td>
      <td>{job.field}</td>
      <td className={job.years === null ? 'num muted' : 'num'}
        title={job.years === null ? "The posting doesn't say, or we don't have its text"
          : 'Years of experience the posting asks for'}>
        {yearsText(job)}
      </td>
      <td className="wrap-narrow">{placeOf(job)}</td>
      <td className="num">{distanceText(job)}</td>
      <td className={mode && mode !== 'not stated' ? undefined : 'muted'}>{mode || '–'}</td>
      <td className="num muted">{ageLabel(ageInDays(job))}</td>
      <td>
        <a href={job.apply_url} target="_blank" rel="noopener noreferrer" onClick={stop}>Apply</a>
      </td>
      <td>
        <label className="applied" onClick={stop}>
          <input type="checkbox" checked={Boolean(job.applied)}
            onChange={(event) => onApplied(job, event.target.checked)} />
          {job.applied && ` ${job.applied}`}
        </label>
      </td>
    </tr>
  )
}
