import { useState, type CSSProperties } from 'react'
import type { Job } from '../api/types'
import {
  ANY_DISTANCE, distanceLabel, distinct, fieldLabel, levelLabel, type Filters,
} from '../logic/jobs'
import { Dropdown } from './Dropdown'
import { MultiSelect } from './MultiSelect'

type Props = {
  jobs: Job[] // all shown jobs, to offer their companies, fields, levels and work modes
  filters: Filters
  onChange: (filters: Filters) => void
  onReset: () => void
}

// The work modes, as modeLabel gives them, in the order people think of them.
const WORK_MODES = [
  { value: 'hybrid', label: 'Hybrid' }, { value: 'on-site', label: 'On-site' },
  { value: 'remote', label: 'Remote' }, { value: 'not stated', label: 'Not stated' },
]

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

// The row of filters above the table: the common ones, and the rest behind
// "More filters".
export function FilterBar({ jobs, filters, onChange, onReset }: Props) {
  // Change one filter, keep the rest.
  const set = (changes: Partial<Filters>) => onChange({ ...filters, ...changes })
  const asOptions = (values: string[]) => distinct(values).map((value) => ({ value }))

  // How many of the filters under "More filters" are in use, so they aren't
  // forgotten while folded away. Folded or open is kept as you leave it.
  const moreInUse = [filters.companies.length > 0, filters.levels.length > 0,
    filters.maxYears !== null, filters.needText, filters.hideApplied,
    filters.flexibleAnywhere && filters.maxKm < ANY_DISTANCE].filter(Boolean).length
  const [showMore, setShowMore] = useState(moreInUse > 0)

  return (
    <div className="filters">
      <div className="filter-row">
        <input type="search" placeholder="Search position or company" value={filters.search}
          onChange={(event) => set({ search: event.target.value })} />

        <MultiSelect label="Fields"
          options={asOptions(jobs.map((job) => job.field)).map(({ value }) => ({ value, label: fieldLabel(value) }))}
          selected={filters.fields} onChange={(fields) => set({ fields })} />
        {/* Every mode is always offered, even one no job in the table has today,
            so a choice never disappears from the list. */}
        <MultiSelect label="Work mode" options={WORK_MODES}
          selected={filters.modes} onChange={(modes) => set({ modes })} />

        <Dropdown value={filters.maxAgeDays} active={filters.maxAgeDays > 0} label="Posted"
          options={AGES.map(({ days, label }) => ({ value: days, label }))}
          onChange={(maxAgeDays) => set({ maxAgeDays })} />

        <Dropdown value={filters.minFit} active={filters.minFit > 0} label="Fit"
          title="Hides jobs scored below this. Jobs without a score stay"
          options={FITS.map(({ fit, label }) => ({ value: fit, label }))}
          onChange={(minFit) => set({ minFit })} />

        <label className="range">
          {/* --fill: how much of the track is coloured, up to the handle (index.css). */}
          <input type="range" min={10} max={ANY_DISTANCE} step={10} value={filters.maxKm}
            aria-label="Maximum distance"
            style={{ '--fill': `${((filters.maxKm - 10) / (ANY_DISTANCE - 10)) * 100}%` } as CSSProperties}
            onChange={(event) => set({ maxKm: Number(event.target.value) })} />
          <span className="distance-label">{distanceLabel(filters.maxKm)}</span>
        </label>

        {/* The filters on the left; what you do with them, apart at the right. */}
        <span className="filter-actions">
          <button className="quiet-button" onClick={() => setShowMore(!showMore)}>
            {showMore ? 'Fewer filters' : 'More filters'}{moreInUse > 0 && ` (${moreInUse} in use)`}
          </button>
          <button className="quiet-button muted" onClick={onReset}>Reset</button>
        </span>
      </div>

      {showMore && (
        <div className="filter-row">
          <MultiSelect label="Companies" options={asOptions(jobs.map((job) => job.company))}
            selected={filters.companies} onChange={(companies) => set({ companies })} />
          <MultiSelect label="Level" options={asOptions(jobs.map(levelLabel))}
            selected={filters.levels} onChange={(levels) => set({ levels })} />

          <Dropdown value={filters.maxYears === null ? '' : String(filters.maxYears)}
            active={filters.maxYears !== null} label="Years asked"
            title="Postings that don't say how many years always stay"
            options={YEARS.map(({ years, label }) => ({ value: years, label }))}
            onChange={(years) => set({ maxYears: years === '' ? null : Number(years) })} />

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

        </div>
      )}
    </div>
  )
}
