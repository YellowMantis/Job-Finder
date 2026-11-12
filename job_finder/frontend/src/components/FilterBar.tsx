import { useState } from 'react'
import type { Job } from '../api/types'
import {
  ANY_DISTANCE, distanceLabel, distinct, levelLabel, modeLabel, type Filters,
} from '../logic/jobs'
import { MultiSelect } from './MultiSelect'

type Props = {
  jobs: Job[] // all shown jobs, to offer their companies, fields, levels and work modes
  filters: Filters
  onChange: (filters: Filters) => void
  onReset: () => void
}

const AGES = [
  { days: 0, label: 'Posted: any time' },
  { days: 3, label: 'Last 3 days' },
  { days: 7, label: 'Last 7 days' },
  { days: 15, label: 'Last 15 days' },
  { days: 30, label: 'Last 30 days' },
  { days: 60, label: 'Last 60 days' },
]

const FITS = [
  { fit: 0, label: 'Fit: any' },
  { fit: 20, label: 'Fit 20%+' },
  { fit: 40, label: 'Fit 40%+' },
  { fit: 60, label: 'Fit 60%+' },
  { fit: 80, label: 'Fit 80%+' },
]

// "" stands for any (a select's values are text).
const YEARS = [
  { years: '', label: 'Years asked: any' },
  { years: '0', label: 'Entry level (0)' },
  ...[1, 2, 3, 5].map((n) => ({ years: String(n), label: `Up to ${n} year${n === 1 ? '' : 's'}` })),
]

// A filter in use is drawn in the accent colour, like a ticked MultiSelect.
const inUse = (used: boolean) => (used ? 'active' : undefined)

// The row of filters above the table: the common ones, and the rest behind
// "More filters".
export function FilterBar({ jobs, filters, onChange, onReset }: Props) {
  // Change one filter, keep the rest.
  const set = (changes: Partial<Filters>) => onChange({ ...filters, ...changes })
  const asOptions = (values: string[]) => distinct(values).map((value) => ({ value }))

  // How many of the filters under "More filters" are in use, so they aren't
  // forgotten while folded away. Folded or open is kept as you leave it.
  const moreInUse = [filters.companies.length > 0, filters.levels.length > 0,
    filters.maxYears !== null, filters.needText, filters.hideApplied, filters.onlyNew,
    filters.flexibleAnywhere && filters.maxKm < ANY_DISTANCE].filter(Boolean).length
  const [showMore, setShowMore] = useState(moreInUse > 0)

  return (
    <div className="filters">
      <div className="filter-row">
        <input type="search" placeholder="Search position or company" value={filters.search}
          onChange={(event) => set({ search: event.target.value })} />

        <MultiSelect label="Fields" options={asOptions(jobs.map((job) => job.field))}
          selected={filters.fields} onChange={(fields) => set({ fields })} />
        <MultiSelect label="Work mode" options={asOptions(jobs.map(modeLabel))}
          selected={filters.modes} onChange={(modes) => set({ modes })} />

        <select value={filters.maxAgeDays} className={inUse(filters.maxAgeDays > 0)}
          onChange={(event) => set({ maxAgeDays: Number(event.target.value) })}>
          {AGES.map(({ days, label }) => <option key={days} value={days}>{label}</option>)}
        </select>

        <select value={filters.minFit} className={inUse(filters.minFit > 0)} title="Hides jobs scored below this. Jobs without a score stay"
          onChange={(event) => set({ minFit: Number(event.target.value) })}>
          {FITS.map(({ fit, label }) => <option key={fit} value={fit}>{label}</option>)}
        </select>

        <label className="range">
          <input type="range" min={10} max={ANY_DISTANCE} step={10} value={filters.maxKm}
            onChange={(event) => set({ maxKm: Number(event.target.value) })} />
          <span className="distance-label">{distanceLabel(filters.maxKm)}</span>
        </label>

        <button className="link-button" onClick={() => setShowMore(!showMore)}>
          {showMore ? 'Fewer filters' : 'More filters'}{moreInUse > 0 && ` (${moreInUse} in use)`}
        </button>
        <button className="link-button" onClick={onReset}>Reset</button>
      </div>

      {showMore && (
        <div className="filter-row">
          <MultiSelect label="Companies" options={asOptions(jobs.map((job) => job.company))}
            selected={filters.companies} onChange={(companies) => set({ companies })} />
          <MultiSelect label="Level" options={asOptions(jobs.map(levelLabel))}
            selected={filters.levels} onChange={(levels) => set({ levels })} />

          <select value={filters.maxYears ?? ''} className={inUse(filters.maxYears !== null)}
            title="Postings that don't say how many years always stay"
            onChange={(event) => set({
              maxYears: event.target.value === '' ? null : Number(event.target.value),
            })}>
            {YEARS.map(({ years, label }) => <option key={years} value={years}>{label}</option>)}
          </select>

          {filters.maxKm < ANY_DISTANCE && (
            <label className="check" title="Hybrid and remote jobs further away: you don't travel there every day">
              <input type="checkbox" checked={filters.flexibleAnywhere}
                onChange={(event) => set({ flexibleAnywhere: event.target.checked })} />
              + hybrid/remote anywhere
            </label>
          )}

          <label className="check">
            <input type="checkbox" checked={filters.needText}
              onChange={(event) => set({ needText: event.target.checked })} />
            Has posting text
          </label>

          <label className="check">
            <input type="checkbox" checked={filters.hideApplied}
              onChange={(event) => set({ hideApplied: event.target.checked })} />
            Hide applied
          </label>

          <label className="check">
            <input type="checkbox" checked={filters.onlyNew}
              onChange={(event) => set({ onlyNew: event.target.checked })} />
            New only
          </label>
        </div>
      )}
    </div>
  )
}
