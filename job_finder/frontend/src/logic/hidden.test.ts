// Tests for searching the Hidden list. Run with: npm test

import { describe, expect, it } from 'vitest'
import type { HiddenJob } from '../api/types'
import { matchingHidden } from './hidden'

const row = (title: string, company: string, reason: string): HiddenJob =>
  ({ url: `https://jobs.example/${title}`, title, company, reason, by_you: false })

const rows = [
  row('Backend Developer', 'Wix', 'Senior: title contains "senior"'),
  row('QA Engineer', 'Monday', 'Older than 30 days: first posted 2026-09-01'),
  row('Data Analyst', 'Wix', 'You hid it: not interested (3 Nov)'),
]

describe('searching the hidden jobs', () => {
  it('finds a company, whatever the letter case', () => {
    expect(matchingHidden(rows, 'wix').map((r) => r.title)).toEqual(['Backend Developer', 'Data Analyst'])
  })

  it('finds a position or a reason', () => {
    expect(matchingHidden(rows, 'QA')).toEqual([rows[1]])
    expect(matchingHidden(rows, 'older than')).toEqual([rows[1]])
    expect(matchingHidden(rows, 'you hid')).toEqual([rows[2]])
  })

  it('shows them all when nothing is typed, and none when nothing matches', () => {
    expect(matchingHidden(rows, '  ')).toEqual(rows)
    expect(matchingHidden(rows, 'Google')).toEqual([])
  })
})
