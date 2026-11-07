// Tests for "Should I apply?" (chance.ts).

import { describe, expect, it } from 'vitest'
import type { Job } from '../api/types'
import { chanceOf, isEntryDoor } from './chance'

function job(changes: Partial<Job> = {}): Job {
  return {
    url: 'https://jobs/1', title: 'Software Engineer', company: 'Acme', field: 'software',
    industry: '', company_size: 'l', city: 'Haifa', location: '', distance_km: 20,
    updated: '2026-11-01', data_level: '', level: 'not stated', level_reason: '',
    industries: {}, has_text: true, apply_url: '', source: '', work_mode: '', fit: null,
    applied: null, years: null, first_seen: '', for_graduates: false, hidden: null,
    hidden_by_you: false, ...changes,
  }
}
const fit = (score: number) => ({
  score, work_mode: '', summary: '', notes: [], requirements: [], years_required: 0,
  model: 'Claude', scored: '', cv: '',
})
const chance = (changes: Partial<Job>) => chanceOf(job(changes)).chance

describe("the AI's judgement", () => {
  it('wins over the rules, with its reason', () => {
    const judged = { ...fit(10), chance: 'apply first' as const, chance_reason: 'Close to the CV' }
    expect(chanceOf(job({ years: 3, fit: judged }))).toEqual({
      chance: 'good', reasons: ['Close to the CV'], guess: false,
    })
  })

  it('is missing in older reviews, so the rules guess and say so', () => {
    expect(chanceOf(job({ years: 1, fit: fit(70) })).guess).toBe(true)
    expect(chanceOf(job({})).guess).toBe(true)
  })
})

describe('how realistic a job is as a first job', () => {
  it('is good for graduates, entry level, up to 2 years, or a junior role', () => {
    expect(chance({ for_graduates: true })).toBe('good')
    expect(chance({ years: 0 })).toBe('good')
    expect(chance({ years: 2 })).toBe('good')
    expect(chance({ level: 'junior' })).toBe('good')
  })

  it('is worth a try at 3 years, or when the posting does not say', () => {
    expect(chance({ years: 3 })).toBe('try')
    expect(chance({})).toBe('try')
  })

  it('is a long shot at 4+ years or a senior role, whatever else', () => {
    expect(chance({ years: 4, fit: fit(90) })).toBe('long')
    expect(chance({ level: 'senior', level_reason: 'title contains "lead"', for_graduates: true }))
      .toBe('long')
  })

  it('is a long shot for internships and PhD roles', () => {
    expect(chance({ title: 'FY27 - Test Automation Engineering Intern', level: 'junior' })).toBe('long')
    expect(chance({ title: 'Student Software Developer' })).toBe('long')
    expect(chance({ title: 'System Engineer - PhD Graduates', for_graduates: true })).toBe('long')
    expect(chance({ title: 'Internal Tools Developer', years: 1 })).toBe('good')
  })

  it('is lifted to good for an entry-door role or a high fit', () => {
    expect(chance({ years: 3, title: 'QA Automation Engineer' })).toBe('good')
    expect(chance({ title: 'Integration Engineer' })).toBe('good')
    expect(chance({ years: 3, fit: fit(50) })).toBe('good')
    expect(chance({ years: 3, fit: fit(49) })).toBe('try')
  })

  it('is lowered to worth a try when the CV shows little of it', () => {
    expect(chance({ years: 1, fit: fit(10) })).toBe('try')
  })

  it('gives its reasons', () => {
    expect(chanceOf(job({ years: 3, title: 'QA Engineer' })).reasons).toEqual([
      'Asks for 3+ years: a little over, often still worth it',
      'A kind of role that often takes people starting out',
    ])
  })
})

describe('entry-door roles', () => {
  it('include testing, integration, support, customer-facing, data and operations roles', () => {
    for (const title of ['QA Engineer', 'Test Automation Developer', 'Validation Engineer',
      'System Integration Engineer', 'Build & Release Engineer', 'Junior DevOps', 'Data Analyst',
      'BI Developer', 'Technical Support Engineer', 'Field Application Engineer',
      'Solutions Engineer', 'Customer Success Engineer', 'Implementation Engineer', 'NOC Operator']) {
      expect(isEntryDoor(title)).toBe(true)
    }
  })

  it('leave out sales roles and plain development', () => {
    for (const title of ['Pre-Sales Solutions Engineer', 'Technical Sales Engineer',
      'Backend Developer', 'Software Engineer']) {
      expect(isEntryDoor(title)).toBe(false)
    }
  })
})
