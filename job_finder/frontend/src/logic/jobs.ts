// The table's rules as plain functions: what a cell says, which jobs pass the
// filters, and in what order. No display code here, so each rule can be
// tested on its own (jobs.test.ts).

import type { Job } from '../api/types'

// ---- Values worked out from a job ---------------------------------------------

// Where the job is: the company site's answer if we have it, else the listing's city.
// Every job is in Israel, so a trailing ", Israel" only makes the column wrap.
export const placeOf = (job: Job) => (job.location || job.city).replace(/,\s*Israel$/i, '')

// Where the place (and so the distance) comes from, for the hover note.
export const placeSource = (job: Job) => job.location
  ? "From the company's own careers site."
  : "From the job listing. Listings often name the company's main office, so the job may be elsewhere."

export const levelLabel = (job: Job) =>
  ({ junior: 'Junior', senior: 'Senior' } as Record<string, string>)[job.level] ?? 'Level not stated'

// Work mode: what the company's own site states, otherwise what the fit review read.
export const modeOf = (job: Job) => job.work_mode || job.fit?.work_mode || ''

// The work mode as the filter offers it: "hybrid", "on-site", "remote" or "not stated".
export const modeLabel = (job: Job) => {
  const mode = modeOf(job)
  return mode && mode !== 'not stated' ? mode : 'not stated'
}

// The fit score, or null when there isn't one (not scored, or couldn't be scored).
export const scoreOf = (job: Job) => job.fit?.score ?? null

// Colour group for a score.
export const fitClass = (score: number) => (score >= 60 ? 'high' : score >= 40 ? 'middle' : 'low')

// "3+", "2.5+", "0" (entry level), or "?" when the posting doesn't say.
export const yearsText = (job: Job) =>
  job.years === null ? '?' : job.years === 0 ? '0' : `${job.years}+`

// Hybrid or remote: you don't travel there every day.
const isFlexible = (job: Job) => ['hybrid', 'remote'].includes(modeLabel(job))

export const distanceText = (job: Job) =>
  job.distance_km === null ? '–' : `${job.distance_km} km`

const DAY = 24 * 60 * 60 * 1000

// Whole days between the listing's date and now (never negative).
export function ageInDays(job: Job, now = Date.now()) {
  return Math.max(0, Math.floor((now - new Date(job.updated).getTime()) / DAY))
}

export function ageLabel(days: number) {
  if (days === 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days} days ago`
}

// A field as people read it: "data-science" is "Data Science", "qa" is "QA".
// The ids stay as they are everywhere else (filters, saved preferences).
const FIELD_NAMES: Record<string, string> = {
  qa: 'QA', devops: 'DevOps', hr: 'HR', 'procurement-operations': 'Procurement & Operations',
}
export const fieldLabel = (field: string) =>
  FIELD_NAMES[field] ?? field.split('-').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')

// "Today", "Yesterday", "3 days ago": ageLabel at the start of a table cell.
export const ageLabelCapital = (days: number) => {
  const label = ageLabel(days)
  return label.charAt(0).toUpperCase() + label.slice(1)
}

// How long ago the listings were downloaded, for the header: "Updated 12m ago".
// `updated` is the back end's local time, "2026-11-25 14:05".
export function updatedLabel(updated: string, now = Date.now()) {
  const minutes = Math.max(0, Math.floor((now - new Date(updated.replace(' ', 'T')).getTime()) / 60000))
  if (minutes < 1) return 'Updated just now'
  if (minutes < 60) return `Updated ${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Updated ${hours}h ago`
  const days = Math.floor(hours / 24)
  return days === 1 ? 'Updated yesterday' : `Updated ${days} days ago`
}

// ---- Filtering ----------------------------------------------------------------

// The distance slider's last position means "any distance".
export const ANY_DISTANCE = 210

export const distanceLabel = (maxKm: number) =>
  maxKm >= ANY_DISTANCE ? 'Any distance' : `Up to ${maxKm} km`

// Each value once, in alphabetical order: the choices for a filter.
export const distinct = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b))

export type Filters = {
  search: string
  companies: string[] // empty means all
  fields: string[]
  levels: string[] // level labels, as levelLabel gives them
  modes: string[] // work modes, as modeLabel gives them
  maxAgeDays: number // 0 means any age
  minFit: number // 0 means any; jobs without a score always pass, they aren't known to fit badly
  maxYears: number | null // null means any; postings that don't say always pass
  needText: boolean
  maxKm: number // ANY_DISTANCE means no limit
  hideApplied: boolean
  flexibleAnywhere: boolean // hybrid and remote jobs pass whatever their distance
}

// The filters to start from: your fields ticked, the default distance.
export const startingFilters = (fields: string[], maxKm: number): Filters => ({
  search: '', companies: [], fields, levels: [], modes: [], maxAgeDays: 0, minFit: 0,
  maxYears: null, needText: false, maxKm, hideApplied: false,
  flexibleAnywhere: false,
})

// The filters you left the app with, on top of the starting ones: a filter
// added since they were saved gets its starting value, and one removed since
// (like the old "Good bets") is dropped.
export function restoredFilters(saved: Partial<Filters> | null, start: Filters): Filters {
  const kept = Object.entries(saved ?? {}).filter(([key]) => key in start)
  const restored = { ...start, ...Object.fromEntries(kept) }
  // Only your fields can be ticked: a field dropped from Settings since is unticked
  // (no fields in Settings means all of them).
  if (!start.fields.length) return restored
  return { ...restored, fields: restored.fields.filter((field) => start.fields.includes(field)) }
}

// The jobs in the fields you chose in Settings: the only ones whose posting
// texts are downloaded, so the only ones the table offers. No fields chosen
// means all of them.
export const inYourFields = (jobs: Job[], fields: string[]) =>
  fields.length ? jobs.filter((job) => fields.includes(job.field)) : jobs

export function passesFilters(job: Job, filters: Filters, now = Date.now()) {
  const search = filters.search.trim().toLowerCase()
  return (
    (scoreOf(job) === null || scoreOf(job)! >= filters.minFit) &&
    (filters.maxYears === null || job.years === null || job.years <= filters.maxYears) &&
    (!filters.hideApplied || !job.applied) &&
    (!search || `${job.title} ${job.company}`.toLowerCase().includes(search)) &&
    (!filters.companies.length || filters.companies.includes(job.company)) &&
    (!filters.fields.length || filters.fields.includes(job.field)) &&
    (!filters.levels.length || filters.levels.includes(levelLabel(job))) &&
    (!filters.modes.length || filters.modes.includes(modeLabel(job))) &&
    (!filters.maxAgeDays || ageInDays(job, now) <= filters.maxAgeDays) &&
    (!filters.needText || job.has_text) &&
    (filters.maxKm >= ANY_DISTANCE || (filters.flexibleAnywhere && isFlexible(job)) ||
      (job.distance_km !== null && job.distance_km <= filters.maxKm))
  )
}

// ---- Sorting ------------------------------------------------------------------

export type SortKey =
  | 'fit' | 'title' | 'company' | 'field' | 'years' | 'place' | 'distance' | 'mode' | 'age'
  | 'applied'
export type Sort = { key: SortKey; descending: boolean }

// What each column sorts by. null means "no value": those rows always go last.
const sortValue: Record<SortKey, (job: Job) => string | number | null> = {
  fit: scoreOf,
  title: (job) => job.title,
  company: (job) => job.company,
  field: (job) => job.field,
  years: (job) => job.years,
  place: placeOf,
  distance: (job) => job.distance_km,
  mode: (job) => modeOf(job) || null,
  age: (job) => ageInDays(job),
  applied: (job) => job.applied,
}

// Rows with no value for the column, in a useful order instead of the file's:
// with no fit yet, the jobs asking for the fewest years come first, then the
// newest. They are the ones a fit run takes from the top, so this decides what
// gets scored first when you haven't sorted the table yourself.
function unscoredOrder(a: Job, b: Job) {
  const age = (job: Job) => (job.updated ? ageInDays(job) : null) // no date: last
  return lowestFirst(a.years, b.years) || lowestFirst(age(a), age(b))
}

// Smaller numbers first, unknown last.
function lowestFirst(x: number | null, y: number | null) {
  if (x === null || y === null) return Number(x === null) - Number(y === null)
  return x - y
}

export function sortJobs(jobs: Job[], sort: Sort) {
  const value = sortValue[sort.key]
  return [...jobs].sort((a, b) => {
    const x = value(a)
    const y = value(b)
    if (x === null && y === null) return sort.key === 'fit' ? unscoredOrder(a, b) : 0
    if (x === null || y === null) return Number(x === null) - Number(y === null)
    const order = typeof x === 'number' && typeof y === 'number'
      ? x - y
      : String(x).localeCompare(String(y))
    return sort.descending ? -order : order
  })
}
