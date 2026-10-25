import { Fragment, useMemo, useState } from 'react'
import type { Job } from '../api/types'
import { reviewedCount, skillGaps } from '../logic/skills'

type Props = {
  jobs: Job[] // the jobs in the table, after the filters
  onOpen: (job: Job) => void
}

const IMPORTANCE: Record<string, string> = { core: 'core', must: 'required', nice: 'nice to have' }

// "What to learn next": the skills the scored jobs in the table ask for that
// your CV doesn't show, most-asked first. Click a skill to see the jobs.
export function SkillGaps({ jobs, onOpen }: Props) {
  const gaps = useMemo(() => skillGaps(jobs), [jobs])
  const [open, setOpen] = useState<string | null>(null) // the skill whose jobs are listed
  const reviewed = reviewedCount(jobs)
  const most = gaps[0]?.gaps.length ?? 1

  if (reviewed === 0) {
    return <p className="empty">No job in the table has a fit score yet. Score some jobs, and
      the skills they ask for that your CV doesn't show will be listed here.</p>
  }

  return (
    <section>
      <p className="note">
        From the fit reviews of the {reviewed} scored job{reviewed === 1 ? '' : 's'} in the table
        (the filters apply). Each skill counts the jobs that ask for it where your CV doesn't show
        it. If you do have one, add it to your CV. Years of experience and degrees aren't counted.
      </p>
      <div className="table-wrap">
        <table className="skills-table">
          <thead>
            <tr>
              <th>Skill</th>
              <th className="num">Jobs missing it</th>
              <th className="num">Required in</th>
              <th className="num">Your CV shows it in</th>
            </tr>
          </thead>
          <tbody>
            {gaps.map(({ skill, gaps: missing, required, met }) => (
              <Fragment key={skill}>
                <tr className="sortable" onClick={() => setOpen(open === skill ? null : skill)}>
                  <td>{open === skill ? '▾' : '▸'} {skill}</td>
                  <td className="num">
                    <span className="skill-bar" style={{ width: `${(60 * missing.length) / most}px` }} />
                    {missing.length}
                  </td>
                  <td className="num">{required}</td>
                  <td className="num muted">{met}</td>
                </tr>
                {open === skill && missing.map((gap) => (
                  <tr key={gap.job.url} className="skill-job" onClick={() => onOpen(gap.job)}>
                    <td className="wrap" colSpan={4}>
                      <strong>{gap.job.title}</strong> · {gap.job.company}
                      <span className="muted"> · asks for “{gap.requirement}” ({IMPORTANCE[gap.importance]}
                        {gap.match === 'partial' ? ', your CV partly shows it' : ''})</span>
                    </td>
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
        {gaps.length === 0 && <p className="empty">No skill gaps among these jobs.</p>}
      </div>
    </section>
  )
}
