// The table's rules as plain functions: what a cell says, which jobs pass the
// filters, and in what order. No display code here, so each rule can be
// tested on its own (jobs.test.ts).

import type { Job } from '../api/types'

// ---- Values worked out from a job ---------------------------------------------

// Where the job is: the company site's answer if we have it, else the listing's city.
export const placeOf = (job: Job) => job.location || job.city

export const levelLabel = (job: Job) =>
  ({ junior: 'Junior', senior: 'Senior' } as Record<string, string>)[job.level] ?? 'Level not stated'

// Work mode: what the company's own site states, otherwise what the fit review read.
export const modeOf = (job: Job) => job.work_mode || job.fit?.work_mode || ''

// The fit score, or null when there isn't one (not scored, or couldn't be scored).
export const scoreOf = (job: Job) => job.fit?.score ?? null

// Colour group for a score.
export const fitClass = (score: number) => (score >= 60 ? 'high' : score >= 40 ? 'middle' : 'low')

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
  maxAgeDays: number // 0 means any age
  needText: boolean
  maxKm: number // ANY_DISTANCE means no limit
  hideApplied: boolean
}

// Filters when the page opens: your fields ticked, the default distance.
export const startingFilters = (fields: string[], maxKm: number): Filters => ({
  search: '', companies: [], fields, levels: [], maxAgeDays: 0, needText: false, maxKm,
  hideApplied: false,
})

export function passesFilters(job: Job, filters: Filters, now = Date.now()) {
  const search = filters.search.trim().toLowerCase()
  return (
    (!filters.hideApplied || !job.applied) &&
    (!search || `${job.title} ${job.company}`.toLowerCase().includes(search)) &&
    (!filters.companies.length || filters.companies.includes(job.company)) &&
    (!filters.fields.length || filters.fields.includes(job.field)) &&
    (!filters.levels.length || filters.levels.includes(levelLabel(job))) &&
    (!filters.maxAgeDays || ageInDays(job, now) <= filters.maxAgeDays) &&
    (!filters.needText || job.has_text) &&
    (filters.maxKm >= ANY_DISTANCE ||
      (job.distance_km !== null && job.distance_km <= filters.maxKm))
  )
}

// ---- Sorting ------------------------------------------------------------------

export type SortKey =
  | 'fit' | 'title' | 'company' | 'field' | 'place' | 'distance' | 'mode' | 'age' | 'applied'
export type Sort = { key: SortKey; descending: boolean }

// What each column sorts by. null means "no value": those rows always go last.
const sortValue: Record<SortKey, (job: Job) => string | number | null> = {
  fit: scoreOf,
  title: (job) => job.title,
  company: (job) => job.company,
  field: (job) => job.field,
  place: placeOf,
  distance: (job) => job.distance_km,
  mode: (job) => modeOf(job) || null,
  age: (job) => ageInDays(job),
  applied: (job) => job.applied,
}

export function sortJobs(jobs: Job[], sort: Sort) {
  const value = sortValue[sort.key]
  return [...jobs].sort((a, b) => {
    const x = value(a)
    const y = value(b)
    if (x === null || y === null) return Number(x === null) - Number(y === null)
    const order = typeof x === 'number' && typeof y === 'number'
      ? x - y
      : String(x).localeCompare(String(y))
    return sort.descending ? -order : order
  })
}
