// "Should I apply?": where to start, in three levels. A different question
// from fit: fit asks whether your CV matches the requirements; this asks
// whether a CV like yours gets called for it.
// A scored job has the AI's judgement, which read the posting and your CV.
// Other jobs get a guess from plain rules on what the row has: postings ask
// for more than they need, so a little over is still worth a try.

import type { Fit, Job } from '../api/types'

export type Chance = 'good' | 'try' | 'long'
// guess: from the rules, not the AI's judgement
export type ChanceReading = { chance: Chance; reasons: string[]; guess: boolean }

export const CHANCE_LABELS: Record<Chance, string> = {
  good: 'Apply first', try: 'Worth sending', long: 'Long shot',
}
const FROM_AI: Record<NonNullable<Fit['chance']>, Chance> = {
  'apply first': 'good', 'worth sending': 'try', 'long shot': 'long',
}
const RANK: Record<Chance, number> = { long: 1, try: 2, good: 3 }
export const chanceRank = (chance: Chance) => RANK[chance]

// Years asked: up to GOOD_YEARS is realistic, LONG_YEARS or more a long shot.
export const GOOD_YEARS = 2
export const LONG_YEARS = 4
// A fit this high lifts "worth a try" to good; this low lowers good to worth a try.
const HIGH_FIT = 50 // the fit of most jobs you applied to
const LOW_FIT = 20

// Roles that often take people starting out: testing and QA, integration and
// deployment, support and customer-facing technical roles, data and operations.
const ENTRY_DOOR = /\b(qa|quality assurance|test(?:ing|er)?|automation|validation|verification|integration|implementation|deployment|build|release|devops|support|customer success|field|application engineer|solutions? engineer|data analyst|bi|business intelligence|noc)\b/i
// Sales roles aren't technical first jobs, even with a technical word in the title.
const SALES = /\b(pre-?sales|sales)\b/i

// Roles not open to a graduate with a first degree: internships (usually for
// students still studying) and roles for PhDs.
const INTERNSHIP = /\b(intern|internship|student)s?\b/i
const PHD = /\bph\.?d\b/i

export const isEntryDoor = (title: string) => ENTRY_DOOR.test(title) && !SALES.test(title)

// The AI's judgement in a review, or null for reviews made before it was asked.
export const aiChance = (fit: Fit): Chance | null => (fit.chance ? FROM_AI[fit.chance] : null)

export function chanceOf(job: Job): ChanceReading {
  const judged = job.fit && aiChance(job.fit)
  if (judged) return { chance: judged, reasons: [job.fit!.chance_reason ?? ''], guess: false }
  return { ...guessed(job), guess: true }
}

function guessed(job: Job): Omit<ChanceReading, 'guess'> {
  const years = job.years
  if (job.level === 'senior') return { chance: 'long', reasons: [`Senior: ${job.level_reason}`] }
  if (INTERNSHIP.test(job.title)) {
    return { chance: 'long', reasons: ['An internship or student role: usually only while still studying'] }
  }
  if (PHD.test(job.title)) return { chance: 'long', reasons: ['A role for PhDs'] }
  if (years !== null && years >= LONG_YEARS) {
    return { chance: 'long', reasons: [`Asks for ${years}+ years of experience`] }
  }

  // The starting point: what the posting asks for.
  let chance: Chance
  const reasons: string[] = []
  if (job.for_graduates) {
    chance = 'good'
    reasons.push('Aimed at graduates')
  } else if (years !== null && years <= GOOD_YEARS) {
    chance = 'good'
    reasons.push(years === 0 ? 'Entry level' : `Asks for ${years}+ years: close to yours`)
  } else if (years !== null) {
    chance = 'try'
    reasons.push(`Asks for ${years}+ years: a little over, often still worth it`)
  } else if (job.level === 'junior') {
    chance = 'good'
    reasons.push('A junior role')
  } else {
    chance = 'try'
    reasons.push("The posting doesn't say how many years")
  }

  // Then the kind of role, and how well your CV fits it.
  if (chance === 'try' && isEntryDoor(job.title)) {
    chance = 'good'
    reasons.push('A kind of role that often takes people starting out')
  }
  const fit = job.fit?.score ?? null
  if (fit !== null && fit >= HIGH_FIT && chance === 'try') {
    chance = 'good'
    reasons.push(`Fits your CV well (${fit}%)`)
  } else if (fit !== null && fit < LOW_FIT && chance === 'good') {
    chance = 'try'
    reasons.push(`Your CV shows little of what it asks for (${fit}%)`)
  }
  return { chance, reasons }
}
