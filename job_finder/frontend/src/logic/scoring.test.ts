import { describe, expect, it } from 'vitest'
import type { BatchRecord, Job } from '../api/types'
import {
  batchesLabel, dayOf, estimate, formatDuration, formatTokens, runProgress, scorable, sessionPercent,
  tokensOf, totalsFor, totalsSince,
} from './scoring'

const batch = (time: string, jobs: number, output_tokens = 1000): BatchRecord => ({
  time, model: 'claude-opus-5-5', jobs, input_tokens: 2, cache_write_tokens: 6000,
  cache_read_tokens: 4000, output_tokens, cost_equivalent_usd: 0.25, seconds: 50,
})

describe('scoring panel', () => {
  it('scores only jobs with text and no current score', () => {
    const job = (url: string, changes: Partial<Job>) => ({ url, ...changes }) as Job
    const fit = { score: 50 } as Job['fit']
    const jobs = [
      job('new', { has_text: true, fit: null }),
      job('no text', { has_text: false, fit: null }),
      job('scored', { has_text: true, fit }),
    ]
    expect(scorable(jobs).map((j) => j.url)).toEqual(['new'])
  })

  it('counts every token of a batch, cached ones included', () => {
    expect(tokensOf(batch('2026-10-18 10:00', 10))).toBe(11002)
    expect(formatTokens(11002)).toBe('11.0k')
    expect(formatTokens(950)).toBe('950')
  })

  it("adds up only the given day's batches", () => {
    const log = [batch('2026-10-17 23:50', 10), batch('2026-10-18 09:00', 10),
      batch('2026-10-18 09:05', 4)]
    const today = totalsFor('2026-10-18', log)
    expect(today.batches).toBe(2)
    expect(today.jobs).toBe(14)
    expect(today.costUsd).toBeCloseTo(0.5)
  })

  it('counts the last 5 hours, a Claude session', () => {
    const now = new Date('2026-10-19T12:00').getTime()
    const log = [batch('2026-10-19 06:30', 10), batch('2026-10-19 08:00', 10), batch('2026-10-19 11:30', 4)]
    expect(totalsSince(now - 5 * 3600 * 1000, log).jobs).toBe(14)   // 06:30 is over 5 hours ago
  })

  it('turns tokens into a share of the session', () => {
    expect(sessionPercent(20000, 0.15)).toBe(3)   // 20 thousand tokens at 0.15% each
  })

  it('writes days the way the log does', () => {
    expect(dayOf(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05')
  })

  it('estimates from the average per job of past batches', () => {
    // Two batches: 14 jobs, 2 x 11002 tokens (one of them 1000 output tokens more).
    const log = [batch('2026-10-18 09:00', 10), batch('2026-10-18 09:05', 4, 2000)]
    const guess = estimate(log, 7)!
    expect(guess.tokens).toBe(Math.round((11002 + 12002) / 14 * 7))
    expect(guess.seconds).toBe(Math.round((50 + 50) / 14 * 7))
  })

  it('has no estimate before any batch, and no time for untimed batches', () => {
    expect(estimate([], 10)).toBeNull()
    const untimed = { ...batch('2026-10-17 03:21', 4), seconds: undefined }
    expect(estimate([untimed], 10)!.seconds).toBeNull()
  })

  it('writes durations and batch counts plainly', () => {
    expect(formatDuration(45)).toBe('45 s')
    expect(formatDuration(200)).toBe('3 min')
    expect(batchesLabel(10, 10)).toBe('1 batch')
    expect(batchesLabel(25, 10)).toBe('3 batches')
  })
})

describe('the progress bar while scoring', () => {
  it('moves with the time taken while a batch is out, but never claims to be finished', () => {
    // 5 jobs in one batch, which usually takes 60 s: no job counted yet, 30 s in.
    expect(runProgress(0, 5, 30, 60)).toEqual({ share: 0.5, secondsLeft: 30 })
    // Slower than usual: it waits at 95% and stops guessing the time left.
    expect(runProgress(0, 5, 90, 60)).toEqual({ share: 0.95, secondsLeft: null })
  })

  it('never shows less than the jobs already counted', () => {
    expect(runProgress(20, 25, 10, 100).share).toBe(0.8)
  })

  it('with no past timings, shows only the counted jobs, or just that it is working', () => {
    expect(runProgress(0, 5, 30, null)).toEqual({ share: null, secondsLeft: null })
    expect(runProgress(10, 20, 30, null)).toEqual({ share: 0.5, secondsLeft: null })
  })
})
