import type { Job } from '../api/types'
import {
  ANY_DISTANCE, distanceLabel, distinct, levelLabel, modeLabel, type Filters,
} from '../logic/jobs'
import { MultiSelect } from './MultiSelect'

type Props = {
  jobs: Job[] // all shown jobs, to offer their companies, fields, levels and work modes
  filters: Filters
  onChange: (filters: Filters) => void
}

const AGES = [
  { days: 0, label: 'Any age' },
  { days: 7, label: 'Last 7 days' },
  { days: 14, label: 'Last 14 days' },
  { days: 30, label: 'Last 30 days' },
]

// The row of filters above the table.
export function FilterBar({ jobs, filters, onChange }: Props) {
  // Change one filter, keep the rest.
  const set = (changes: Partial<Filters>) => onChange({ ...filters, ...changes })
  const asOptions = (values: string[]) => distinct(values).map((value) => ({ value }))

  return (
    <div className="filters">
      <input type="search" placeholder="Search position or company" value={filters.search}
        onChange={(event) => set({ search: event.target.value })} />

      <MultiSelect label="Companies" options={asOptions(jobs.map((job) => job.company))}
        selected={filters.companies} onChange={(companies) => set({ companies })} />
      <MultiSelect label="Fields" options={asOptions(jobs.map((job) => job.field))}
        selected={filters.fields} onChange={(fields) => set({ fields })} />
      <MultiSelect label="Level" options={asOptions(jobs.map(levelLabel))}
        selected={filters.levels} onChange={(levels) => set({ levels })} />
      <MultiSelect label="Work mode" options={asOptions(jobs.map(modeLabel))}
        selected={filters.modes} onChange={(modes) => set({ modes })} />

      <select className="age-filter" value={filters.maxAgeDays}
        onChange={(event) => set({ maxAgeDays: Number(event.target.value) })}>
        {AGES.map(({ days, label }) => <option key={days} value={days}>{label}</option>)}
      </select>

      <label className="check">
        <input type="checkbox" checked={filters.needText}
          onChange={(event) => set({ needText: event.target.checked })} />
        Has posting text
      </label>

      <label className="range">
        <input type="range" min={10} max={ANY_DISTANCE} step={10} value={filters.maxKm}
          onChange={(event) => set({ maxKm: Number(event.target.value) })} />
        <span className="distance-label">{distanceLabel(filters.maxKm)}</span>
      </label>

      <label className="check">
        <input type="checkbox" checked={filters.hideApplied}
          onChange={(event) => set({ hideApplied: event.target.checked })} />
        Hide applied
      </label>
    </div>
  )
}
