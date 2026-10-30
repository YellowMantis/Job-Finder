// Tests for "Missing skills". Requirements are real ones from fit reviews.

import { describe, expect, it } from 'vitest'
import type { Fit, Job, Requirement } from '../api/types'
import { skillGaps, skillsNamedIn } from './skills'

const need = (requirement: string, match: Requirement['match'], evidence = 'not in CV',
  importance: Requirement['importance'] = 'must'): Requirement =>
  ({ requirement, match, evidence, importance })

const job = (url: string, requirements: Requirement[]) =>
  ({ url, title: url, company: 'Acme', fit: { requirements } as Fit }) as Job

const counts = (jobs: Job[]) =>
  Object.fromEntries(skillGaps(jobs).map((gap) => [gap.skill, gap.gaps.length]))

describe('naming skills in a requirement', () => {
  it('finds every skill a requirement names, however it is spelled', () => {
    expect(skillsNamedIn('DevSecOps tools (Kubernetes, Artifactory, GitHub Actions)'))
      .toEqual(['Kubernetes', 'CI/CD'])
    expect(skillsNamedIn('Python and C/C++ on Linux')).toEqual(['Python', 'C++', 'C', 'Linux'])
  })

  it("doesn't mistake one name for another", () => {
    expect(skillsNamedIn('Google Workspace administration')).not.toContain('Go')
    expect(skillsNamedIn('CI/CD pipelines')).not.toContain('C')
    expect(skillsNamedIn('JavaScript and React')).not.toContain('Java')
    expect(skillsNamedIn('Data pipelines in Airflow')).not.toContain('CI/CD')
  })

  it('leaves out years of experience and degrees', () => {
    expect(skillsNamedIn('3+ years of experience with Python')).toEqual([])
    expect(skillsNamedIn('B.Sc. in Computer Science or Electrical Engineering')).toEqual([])
  })
})

describe('counting the gaps', () => {
  it('counts each job once per skill, most-asked first', () => {
    const jobs = [
      job('a', [need('Kubernetes and Helm', 'no'), need('Kubernetes operators', 'no')]),
      job('b', [need('Kubernetes', 'no'), need('Kafka', 'no', 'not in CV', 'nice')]),
    ]
    expect(counts(jobs)).toEqual({ Kubernetes: 2, Helm: 1, 'Kafka / streaming': 1 })
    expect(skillGaps(jobs)[0].skill).toBe('Kubernetes')
  })

  it('a partial match leaves out the skills its evidence shows the CV has', () => {
    const jobs = [job('a', [need('SQL, networking, Linux/Windows servers', 'partial', 'SQL; Linux CLI')])]
    expect(counts(jobs)).toEqual({ Networking: 1, 'Windows / IT administration': 1 })
  })

  it('a skill the CV shows in one requirement is not a gap in another of the same job', () => {
    const jobs = [job('a', [need('Python', 'yes', 'Python'), need('Python and Go services', 'no')])]
    expect(counts(jobs)).toEqual({ Go: 1 })
    const python = skillGaps([job('b', [need('Python', 'no')]), ...jobs]).find((gap) => gap.skill === 'Python')
    expect(python).toMatchObject({ met: 1, gaps: [{ job: { url: 'b' } }] })
  })

  it('counts how many jobs require the skill, not only list it as nice to have', () => {
    const jobs = [job('a', [need('Docker', 'no')]), job('b', [need('Docker', 'no', '', 'nice')])]
    expect(skillGaps(jobs)[0]).toMatchObject({ skill: 'Docker', required: 1 })
  })

  it('ignores jobs without a review', () => {
    expect(skillGaps([{ url: 'x', fit: null } as Job])).toEqual([])
  })
})
