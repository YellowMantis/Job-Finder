// "Missing skills": the skills that scored jobs ask for and your CV doesn't
// show, counted across the jobs in the table. It only reads the fit reviews
// already saved, so it costs no AI usage.
//
// A review's requirements are free text ("Kubernetes and Helm", "DevSecOps
// tools (Kubernetes, Artifactory, GitHub Actions)"), worded differently in
// every job. So each skill below is a name plus the spellings that mean it,
// and a requirement counts for every skill it names.

import type { Importance, Job, Match, Requirement } from '../api/types'

// [name, pattern]. Patterns ignore case unless they say otherwise; \b keeps
// "Go" from matching inside "Google" and "C" from matching inside "CI/CD".
const SKILL_PATTERNS: [string, RegExp][] = [
  ['Python', /\bpython\b/i],
  ['C++', /c\+\+/i],
  ['C', /\bC\b(?![+#])/], // capital C on its own: "C", "C/C++", but not "C++", "C#" or "CI/CD"
  ['C#', /c#|\.net\b/i],
  ['Java', /\bjava\b(?!script)/i],
  ['Go', /\bgolang\b|\bGo\b/],
  ['JavaScript', /javascript|\bjs\b/i],
  ['TypeScript', /typescript/i],
  ['React', /\breact\b/i],
  ['Node.js', /node\.?js/i],
  ['SQL', /\bsql\b(?! server)|postgres|mysql/i],
  ['NoSQL', /nosql|mongo|redis|cassandra|dynamodb/i],
  ['Elasticsearch', /elastic/i],
  ['Linux', /linux/i],
  ['Bash / shell scripting', /\bbash\b|\bshell\b|scripting/i],
  ['Git', /\bgit\b/i],
  ['Docker', /docker|container/i],
  ['Kubernetes', /kubernetes|\bk8s\b/i],
  ['Helm', /\bhelm\b/i],
  ['Terraform / infrastructure as code', /terraform|\biac\b|infrastructure as code|pulumi|ansible/i],
  ['CI/CD', /ci\/cd|jenkins|github actions|gitlab|argo ?cd/i],
  ['AWS', /\baws\b|amazon web services/i],
  ['Google Cloud', /\bgcp\b|google cloud/i],
  ['Azure', /azure/i],
  ['Cloud (general)', /\bcloud\b(?!-native)/i],
  ['Monitoring / observability', /monitoring|observability|grafana|prometheus|datadog/i],
  ['Kafka / streaming', /kafka|streaming|flink/i],
  ['Spark / big data', /spark|big data|hadoop|airflow/i],
  ['Distributed systems', /distributed|large-scale|high scale|scalab/i],
  ['Microservices', /microservice/i],
  ['REST APIs', /\bapis?\b|\brest\b/i],
  ['Networking', /network|tcp\/ip|\bdns\b|l2\/l3|ethernet|protocols?\b/i],
  ['Security', /security|cyber|penetration|vulnerab/i],
  ['Machine learning', /machine learning|\bml\b|ai\/ml|deep learning|pytorch|tensorflow|scikit|\bnlp\b|forecasting|time-series/i],
  ['LLMs / generative AI', /\bllms?\b|genai|generative|\brag\b|agentic|\bagents?\b|prompt|\bmcp\b|embedding/i],
  ['AI coding tools', /ai-assisted|cursor|claude|copilot/i],
  ['Computer vision', /computer vision|image processing|\bvision\b/i],
  ['Data analysis', /pandas|numpy|statistic|data analy|analytics/i],
  ['MATLAB', /matlab/i],
  ['Test automation', /test automation|automation framework|automated test|playwright|selenium|pytest|cypress/i],
  ['QA / testing', /\bqa\b|\btesting\b|test plans?|istqb/i],
  ['Embedded / firmware', /embedded|firmware|rtos|microcontroller|\bspi\b|\bi2c\b|\buart\b/i],
  ['Linux kernel / drivers', /kernel|drivers?\b|low-level/i],
  ['FPGA / chip design', /fpga|verilog|vhdl|asic|\bic\b|silicon|rtl\b|\beda\b|orcad|allegro/i],
  ['Electronics / lab equipment', /electronic|oscilloscope|lab equipment|schematic|pcb|measurement|labview/i],
  ['RF / signal processing', /\brf\b|\bdsp\b|signal processing|wireless|modem/i],
  ['Mechanical / CAD', /mechanical|solidworks|\bcad\b|creo|technical drawings/i],
  ['Semiconductor / manufacturing', /semiconductor|cleanroom|manufacturing|production line/i],
  ['Windows / IT administration', /windows|active directory|m365|microsoft 365|google workspace|it support/i],
  ['Mobile apps', /mobile|android|\bios\b|swift|kotlin/i],
  ['Multithreading / performance', /multithread|concurren|performance|real-time/i],
  ['Object-oriented design', /\boop\b|object[- ]oriented|design patterns/i],
  ['Algorithms and data structures', /algorithm|data structure/i],
  ['Excel / Office', /excel\b|microsoft office|\boffice\b/i],
  ['Agile / Jira', /agile|scrum|jira/i],
  ['Salesforce / CRM', /salesforce|\bcrm\b|hubspot/i],
  ['Hebrew', /hebrew/i],
  ['English', /english/i],
]

// A requirement your CV doesn't fully meet, with the job it came from.
export type Gap = {
  job: Job
  requirement: string
  importance: Importance
  match: Exclude<Match, 'yes'>
}

export type SkillGap = {
  skill: string
  gaps: Gap[] // one per job: the job's most important unmet requirement naming it
  required: number // of those, jobs where it is a must or core requirement
  met: number // jobs that ask for it where your CV already shows it
}

// Years of experience have their own column and filter, and degrees aren't
// something to learn next, so neither is counted here.
const NOT_A_SKILL = /\byears?\b|\bdegree\b|b\.?sc|m\.?sc|ph\.?d|bachelor|master/i

const named = (skill: string, text: string) =>
  SKILL_PATTERNS.some(([name, pattern]) => name === skill && pattern.test(text))

export const skillsNamedIn = (requirement: string) =>
  NOT_A_SKILL.test(requirement) ? [] :
    SKILL_PATTERNS.filter(([, pattern]) => pattern.test(requirement)).map(([skill]) => skill)

// Does this requirement show the CV has the skill? A full match does. A
// partial one does when its evidence (the CV's own words) names the skill:
// "SQL, networking, Linux servers" with evidence "SQL; Linux CLI" shows SQL
// and Linux, and leaves networking as the gap.
const shows = (skill: string, requirement: Requirement) =>
  requirement.match === 'yes' || (requirement.match === 'partial' && named(skill, requirement.evidence))

const RANK: Record<Importance, number> = { core: 0, must: 1, nice: 2 }

// The skills the jobs ask for and your CV doesn't show, most jobs first. Each
// job counts once per skill, and not at all if any of its requirements shows
// the CV has the skill.
export function skillGaps(jobs: Job[]): SkillGap[] {
  const bySkill = new Map<string, { gaps: Map<string, Gap>; met: Set<string> }>()
  for (const job of jobs) {
    for (const requirement of job.fit?.requirements ?? []) {
      for (const skill of skillsNamedIn(requirement.requirement)) {
        const entry = bySkill.get(skill) ?? { gaps: new Map<string, Gap>(), met: new Set<string>() }
        bySkill.set(skill, entry)
        if (shows(skill, requirement)) {
          entry.met.add(job.url)
          continue
        }
        const earlier = entry.gaps.get(job.url)
        if (!earlier || RANK[requirement.importance] < RANK[earlier.importance]) {
          entry.gaps.set(job.url, { job, requirement: requirement.requirement,
            importance: requirement.importance, match: requirement.match as Gap['match'] })
        }
      }
    }
  }
  return [...bySkill.entries()]
    .map(([skill, { gaps, met }]) => {
      const missing = [...gaps.values()].filter((gap) => !met.has(gap.job.url))
      return {
        skill,
        gaps: missing,
        required: missing.filter((gap) => gap.importance !== 'nice').length,
        met: met.size,
      }
    })
    .filter((entry) => entry.gaps.length > 0)
    .sort((a, b) => b.required - a.required || b.gaps.length - a.gaps.length
      || a.skill.localeCompare(b.skill))
}

// How many jobs in the list have a fit review to learn from.
export const reviewedCount = (jobs: Job[]) => jobs.filter((job) => job.fit).length
