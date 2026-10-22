// The scoring panel's rules as plain functions (tested in scoring.test.ts).

import type { BatchRecord, Job } from '../api/types'

// Jobs that can be scored: they have posting text, and no score for this CV
// yet. A score stays valid whichever AI connection made it.
export const scorable = (jobs: Job[]) => jobs.filter((job) => job.has_text && !job.fit)

// Every token a batch used. Cached tokens count too: they are cheaper, but
// still part of the session.
export const tokensOf = (batch: BatchRecord) =>
  batch.input_tokens + batch.cache_write_tokens + batch.cache_read_tokens + batch.output_tokens

// 23456 -> "23.5k"
export const formatTokens = (tokens: number) =>
  tokens < 1000 ? String(tokens) : `${(tokens / 1000).toFixed(1)}k`

export type Totals = { batches: number; jobs: number; tokens: number; costUsd: number }

// What scoring used on one day ("2026-10-18").
export function totalsFor(day: string, log: BatchRecord[]): Totals {
  const batches = log.filter((batch) => batch.time.startsWith(day))
  return {
    batches: batches.length,
    jobs: batches.reduce((sum, batch) => sum + batch.jobs, 0),
    tokens: batches.reduce((sum, batch) => sum + tokensOf(batch), 0),
    costUsd: batches.reduce((sum, batch) => sum + batch.cost_equivalent_usd, 0),
  }
}

// A Claude plan's usage limit resets every 5 hours: what was used in that window.
export const SESSION_HOURS = 5

export function totalsSince(since: number, log: BatchRecord[]): Totals {
  const batches = log.filter((batch) => new Date(batch.time.replace(' ', 'T')).getTime() >= since)
  return {
    batches: batches.length,
    jobs: batches.reduce((sum, batch) => sum + batch.jobs, 0),
    tokens: batches.reduce((sum, batch) => sum + tokensOf(batch), 0),
    costUsd: batches.reduce((sum, batch) => sum + batch.cost_equivalent_usd, 0),
  }
}

// What share of a 5-hour session these tokens would use, from a calibration.
export const sessionPercent = (tokens: number, percentPer1k: number) =>
  Math.round((tokens / 1000) * percentPer1k * 10) / 10

// The day of a date, in local time, as the log writes it: "2026-10-18".
export function dayOf(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export type Estimate = { tokens: number; seconds: number | null }

// What scoring `count` jobs will probably use, from the average per job of
// past batches. null when there is no past batch to go by.
export function estimate(log: BatchRecord[], count: number): Estimate | null {
  const batches = log.filter((batch) => batch.jobs > 0)
  const jobs = batches.reduce((sum, batch) => sum + batch.jobs, 0)
  if (!jobs) return null
  const tokens = batches.reduce((sum, batch) => sum + tokensOf(batch), 0)
  // Only newer batches record their time.
  const timed = batches.filter((batch) => batch.seconds !== undefined)
  const timedJobs = timed.reduce((sum, batch) => sum + batch.jobs, 0)
  const seconds = timed.reduce((sum, batch) => sum + (batch.seconds ?? 0), 0)
  return {
    tokens: Math.round((tokens / jobs) * count),
    seconds: timedJobs ? Math.round((seconds / timedJobs) * count) : null,
  }
}

// 45 -> "45 s", 200 -> "3 min"
export const formatDuration = (seconds: number) =>
  seconds < 90 ? `${seconds} s` : `${Math.round(seconds / 60)} min`

// How far a scoring run has got, for the progress bar. Jobs only count as done
// when their whole batch is back (one request reviews up to 10), so between
// batches the bar moves with the time taken, against how long past batches
// took. It stops at 95% until the run really ends. share is null when there's
// nothing to go by (no past timings): the bar then just shows it's working.
export function runProgress(done: number, total: number, elapsed: number, expected: number | null) {
  if (!total) return { share: null, secondsLeft: null }
  const counted = done / total
  if (!expected) return { share: done ? counted : null, secondsLeft: null }
  return {
    share: Math.max(counted, Math.min(0.95, elapsed / expected)),
    secondsLeft: elapsed < expected ? Math.round(expected - elapsed) : null,
  }
}

// "1 batch", "3 batches"
export function batchesLabel(count: number, batchSize: number) {
  const batches = Math.ceil(count / batchSize)
  return `${batches} batch${batches === 1 ? '' : 'es'}`
}
