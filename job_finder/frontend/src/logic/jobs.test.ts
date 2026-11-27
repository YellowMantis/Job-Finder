// Tests for the table's rules. Run with: npm test

import { describe, expect, it } from 'vitest'
import type { Job } from '../api/types'
import {
  ANY_DISTANCE, ageInDays, ageLabel, ageLabelCapital, distanceLabel, fieldLabel, distinct, inYourFields, modeLabel, modeOf, onLinkedIn, placeSource,
  passesFilters,
  placeOf, restoredFilters, sortJobs, updatedLabel, yearsText,
  type Filters,
} from './jobs'

// A job with sensible defaults; each test changes only what it is about.
function job(changes: Partial<Job> = {}): Job {
  return {
    url: 'https://example.com/1', title: 'Software Engineer', company: 'VAST Data',
    field: 'software', industry: '', company_size: 'l', city: 'תל אביב-יפו', location: '',
    distance_km: 40, updated: '2026-10-10', data_level: '', level: 'not stated',
    level_reason: '', industries: {}, has_text: true, apply_url: '', source: '',
    work_mode: '', fit: null, applied: null, years: null, first_seen: '', for_graduates: false,
    hidden: null, hidden_by_you: false,
    ...changes,
  }
}

const noFilters: Filters = {
  search: '', companies: [], fields: [], levels: [], modes: [], maxAgeDays: 0, minFit: 0,
  maxYears: null, needText: false, maxKm: ANY_DISTANCE, hideApplied: false,
  flexibleAnywhere: false,
}

const fit = (score: number | null, work_mode = 'not stated') => ({
  score, work_mode, summary: '', notes: [], requirements: [], years_required: 0,
  model: 'Claude', scored: '', cv: '',
})

describe('values shown in the table', () => {
  it("prefers the company site's location to the listing's city", () => {
    expect(placeOf(job({ location: 'Haifa' }))).toBe('Haifa')
    expect(placeOf(job())).toBe('תל אביב-יפו')
  })

  it('leaves out the country, since every job is in Israel', () => {
    expect(placeOf(job({ location: 'Tel Aviv-Jaffa, Israel' }))).toBe('Tel Aviv-Jaffa')
    expect(placeOf(job({ location: 'Tel Aviv/ Netanya,Israel' }))).toBe('Tel Aviv/ Netanya')
  })

  it("prefers the site's work mode to the review's reading", () => {
    expect(modeOf(job({ work_mode: 'hybrid', fit: fit(50, 'remote') }))).toBe('hybrid')
    expect(modeOf(job({ fit: fit(50, 'remote') }))).toBe('remote')
    expect(modeOf(job())).toBe('')
  })

  it('counts whole days since the listing was updated', () => {
    const now = new Date('2026-10-17T12:00:00Z').getTime()
    expect(ageInDays(job({ updated: '2026-10-17' }), now)).toBe(0)
    expect(ageInDays(job({ updated: '2026-10-10' }), now)).toBe(7)
    expect(ageLabel(1)).toBe('yesterday')
    expect(ageLabel(7)).toBe('7 days ago')
  })

  it("says whether a job's place is the company's own or only the listing's", () => {
    expect(placeSource(job({ location: 'Ramat Hasharon, Israel' }))).toMatch(/company's own/)
    expect(placeSource(job({ location: '' }))).toMatch(/main office/)
  })

  it('knows a job whose posting is on LinkedIn', () => {
    expect(onLinkedIn(job({ url: 'https://il.linkedin.com/jobs/view/qa-engineer-at-acme-123' }))).toBe(true)
    expect(onLinkedIn(job({ url: 'https://www.linkedin.com/jobs/view/1', apply_url: '' }))).toBe(true)
    // the company's own page found for it: not a LinkedIn job any more
    expect(onLinkedIn(job({ url: 'https://il.linkedin.com/jobs/view/1', apply_url: 'https://boards.greenhouse.io/acme/1' }))).toBe(false)
    expect(onLinkedIn(job({ url: 'https://www.comeet.com/jobs/acme/AB.001/qa/1' }))).toBe(false)
    expect(onLinkedIn(job({ url: 'https://notlinkedin.com.example/jobs/1' }))).toBe(false)
  })

  it('names fields and ages as people read them', () => {
    expect(fieldLabel('data-science')).toBe('Data Science')
    expect(fieldLabel('qa')).toBe('QA')
    expect(fieldLabel('devops')).toBe('DevOps')
    expect(fieldLabel('procurement-operations')).toBe('Procurement & Operations')
    expect(fieldLabel('software')).toBe('Software')
    expect(ageLabelCapital(1)).toBe('Yesterday')
    expect(ageLabelCapital(0)).toBe('Today')
  })

  it('says how long ago the listings were updated', () => {
    const now = new Date('2026-11-25T14:30:00').getTime() // local time, as the back end writes it
    expect(updatedLabel('2026-11-25 14:30', now)).toBe('Updated just now')
    expect(updatedLabel('2026-11-25 14:18', now)).toBe('Updated 12m ago')
    expect(updatedLabel('2026-11-25 09:10', now)).toBe('Updated 5h ago')
    expect(updatedLabel('2026-11-24 10:00', now)).toBe('Updated yesterday')
    expect(updatedLabel('2026-11-20 14:30', now)).toBe('Updated 5 days ago')
  })
})

describe('filters', () => {
  it('shows everything when nothing is set', () => {
    expect(passesFilters(job(), noFilters)).toBe(true)
  })

  it('keeps jobs within the distance, and drops jobs with no distance', () => {
    const filters = { ...noFilters, maxKm: 50 }
    expect(passesFilters(job({ distance_km: 50 }), filters)).toBe(true)
    expect(passesFilters(job({ distance_km: 51 }), filters)).toBe(false)
    expect(passesFilters(job({ distance_km: null }), filters)).toBe(false)
  })

  it('keeps jobs with no distance when any distance is allowed', () => {
    expect(passesFilters(job({ distance_km: null }), noFilters)).toBe(true)
  })

  it('searches title and company, ignoring case', () => {
    const filters = { ...noFilters, search: 'vast' }
    expect(passesFilters(job(), filters)).toBe(true)
    expect(passesFilters(job({ company: 'Nvidia' }), filters)).toBe(false)
  })

  it('can hide jobs you applied to', () => {
    const filters = { ...noFilters, hideApplied: true }
    expect(passesFilters(job({ applied: '2026-10-15' }), filters)).toBe(false)
  })

  it("filters by work mode, the site's own or else the review's", () => {
    const filters = { ...noFilters, modes: ['hybrid', 'not stated'] }
    expect(passesFilters(job({ work_mode: 'hybrid' }), filters)).toBe(true)
    expect(passesFilters(job({ work_mode: 'on-site' }), filters)).toBe(false)
    expect(passesFilters(job(), filters)).toBe(true) // nothing known: "not stated"
    const reviewedRemote = job({ fit: { work_mode: 'remote' } as Job['fit'] })
    expect(modeLabel(reviewedRemote)).toBe('remote')
    expect(passesFilters(reviewedRemote, filters)).toBe(false)
  })
})


describe('fit, years and distance filters', () => {
  const scored = (score: number, years: number | null = null) => job({ fit: fit(score), years })

  it("can hide jobs scored below a minimum, and keeps the ones without a score", () => {
    const filters = { ...noFilters, minFit: 40 }
    expect(passesFilters(scored(40), filters)).toBe(true)
    expect(passesFilters(scored(39), filters)).toBe(false)
    expect(passesFilters(job(), filters)).toBe(true) // not scored, or no text to score
  })

  it("can keep only jobs asking for at most some years, and ones that don't say", () => {
    const filters = { ...noFilters, maxYears: 2 }
    expect(passesFilters(job({ years: 2 }), filters)).toBe(true)
    expect(passesFilters(job({ years: 3 }), filters)).toBe(false)
    expect(passesFilters(job({ years: null }), filters)).toBe(true)
    expect(passesFilters(job({ years: 0 }), { ...noFilters, maxYears: 0 })).toBe(true)
  })

  it('combines them: 40%+, up to 3 years', () => {
    const filters = { ...noFilters, minFit: 40, maxYears: 3 }
    expect(passesFilters(scored(55, 3), filters)).toBe(true)
    expect(passesFilters(scored(70, 5), filters)).toBe(false)
  })

  it('can keep hybrid and remote jobs beyond the distance', () => {
    const far = { ...noFilters, maxKm: 50 }
    const hybrid = job({ distance_km: 120, work_mode: 'hybrid' })
    expect(passesFilters(hybrid, far)).toBe(false)
    expect(passesFilters(hybrid, { ...far, flexibleAnywhere: true })).toBe(true)
    expect(passesFilters(job({ distance_km: 120, work_mode: 'on-site' }),
      { ...far, flexibleAnywhere: true })).toBe(false)
  })
})

describe('sorting', () => {
  it('puts the best fit first, and unscored jobs last', () => {
    const jobs = [job({ url: 'a', fit: fit(40) }), job({ url: 'b' }), job({ url: 'c', fit: fit(90) })]
    const sorted = sortJobs(jobs, { key: 'fit', descending: true })
    expect(sorted.map((j) => j.url)).toEqual(['c', 'a', 'b'])
  })

  it('orders the unscored jobs by fewest years asked, then newest', () => {
    const jobs = [
      job({ url: 'scored', fit: fit(50), years: 9 }),
      job({ url: '3y', years: 3, updated: '2026-11-01' }),
      job({ url: '?', years: null, updated: '2026-11-10' }),
      job({ url: '1y old', years: 1, updated: '2026-09-01' }),
      job({ url: '1y new', years: 1, updated: '2026-11-05' }),
      job({ url: '1y no date', years: 1, updated: '' }),
    ]
    expect(sortJobs(jobs, { key: 'fit', descending: true }).map((j) => j.url))
      .toEqual(['scored', '1y new', '1y old', '1y no date', '3y', '?'])
  })

  it('keeps unknown distances last in either direction', () => {
    const jobs = [job({ url: 'far', distance_km: 90 }), job({ url: '?', distance_km: null }),
      job({ url: 'near', distance_km: 10 })]
    expect(sortJobs(jobs, { key: 'distance', descending: false }).map((j) => j.url))
      .toEqual(['near', 'far', '?'])
    expect(sortJobs(jobs, { key: 'distance', descending: true }).map((j) => j.url))
      .toEqual(['far', 'near', '?'])
  })

  it("sorts by years asked, the ones that don't say last", () => {
    const jobs = [job({ url: '5', years: 5 }), job({ url: '?', years: null }), job({ url: '0', years: 0 })]
    expect(sortJobs(jobs, { key: 'years', descending: false }).map((j) => j.url)).toEqual(['0', '5', '?'])
    expect(yearsText(jobs[0])).toBe('5+')
    expect(yearsText(jobs[1])).toBe('?')
    expect(yearsText(jobs[2])).toBe('0')
  })

  it('does not change the list it was given', () => {
    const jobs = [job({ url: 'b', title: 'B' }), job({ url: 'a', title: 'A' })]
    sortJobs(jobs, { key: 'title', descending: false })
    expect(jobs[0].url).toBe('b')
  })
})

describe('filter choices', () => {
  it('offers each value once, in order', () => {
    expect(distinct(['qa', 'software', 'qa', 'devops'])).toEqual(['devops', 'qa', 'software'])
  })

  it("labels the slider's last position as any distance", () => {
    expect(distanceLabel(50)).toBe('Up to 50 km')
    expect(distanceLabel(ANY_DISTANCE)).toBe('Any distance')
  })
})

describe('filters you left the app with', () => {
  const start = { ...noFilters, maxKm: 50 }

  it('start from the defaults when none were saved', () => {
    expect(restoredFilters(null, start)).toEqual(start)
  })

  it('keep your choices, give new filters their starting value, and drop old ones', () => {
    const saved = { minFit: 40, modes: ['hybrid'], goodBets: true } as Partial<Filters>
    const restored = restoredFilters(saved, start)
    expect(restored.minFit).toBe(40)
    expect(restored.modes).toEqual(['hybrid'])
    expect(restored.maxKm).toBe(50)
    expect('goodBets' in restored).toBe(false)
  })

  it('untick a field that is no longer one of yours', () => {
    const yours = { ...start, fields: ['software', 'qa'] }
    expect(restoredFilters({ fields: ['qa', 'design'] }, yours).fields).toEqual(['qa'])
    // No fields in Settings means all: nothing to untick.
    expect(restoredFilters({ fields: ['design'] }, start).fields).toEqual(['design'])
  })
})

describe('your fields', () => {
  const jobs = [job({ field: 'software' }), job({ field: 'design' }), job({ field: 'qa' })]

  it('keep only the jobs in the fields you chose in Settings', () => {
    expect(inYourFields(jobs, ['software', 'qa']).map((j) => j.field)).toEqual(['software', 'qa'])
  })

  it('keep every job when no fields are chosen', () => {
    expect(inYourFields(jobs, [])).toHaveLength(3)
  })
})
