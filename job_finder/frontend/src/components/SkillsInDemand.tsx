import { useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Job } from '../api/types'
import { useLoadedWhenShown } from '../hooks/useLoadedWhenShown'
import { fieldLabel } from '../logic/jobs'
import { Dropdown } from './Dropdown'

type Props = {
  jobs: Job[] // every shown job, to open one from the list
  onOpen: (job: Job) => void
  shown: boolean // this tab is the one on screen
  version: string // changes whenever the shown jobs may have changed
}

type Show = 'all' | 'missing' | 'have'

// The Skills tab: the skills the jobs in your fields ask for, most asked first, read
// from the posting texts (no AI), and whether your CV names each one.
export function SkillsInDemand({ jobs, onOpen, shown, version }: Props) {
  const [answer] = useLoadedWhenShown(api.skills, shown, version)
  const [field, setField] = useState('') // '' is all your fields
  const [show, setShow] = useState<Show>('all')
  const [open, setOpen] = useState<string | null>(null) // the skill whose jobs are listed

  const counted = useMemo(() => answer?.jobs.filter((job) => !field || job.field === field) ?? [],
    [answer, field])
  const rows = useMemo(() => {
    if (!answer) return []
    return answer.skills
      .map((skill) => ({ skill, urls: counted.filter((job) => job.skills.includes(skill)).map((job) => job.url) }))
      .filter((row) => row.urls.length > 0)
      .sort((a, b) => b.urls.length - a.urls.length)
  }, [answer, counted])

  if (!answer) return <p className="empty">Reading the postings…</p>
  const cv = answer.cv
  const fields = [...new Set(answer.jobs.map((job) => job.field))].sort()
  const most = rows[0]?.urls.length ?? 1
  const byUrl = new Map(jobs.map((job) => [job.url, job]))
  const visible = rows.filter(({ skill }) =>
    show === 'all' || !cv || (show === 'have') === cv.includes(skill))

  return (
    <section className="skills-demand">
      <div className="skills-head">
        <p className="note">
          Skills asked for in {counted.length.toLocaleString('en-US')} postings
          {field ? ` in ${fieldLabel(field)}` : ' in your fields'}, read from their requirements.
          Jobs without posting text aren't counted.
        </p>
        <div className="skills-controls">
          <Dropdown value={field} label="Field"
            options={[{ value: '', label: 'All your fields' },
              ...fields.map((name) => ({ value: name, label: fieldLabel(name) }))]}
            onChange={(chosen) => { setField(chosen); setOpen(null) }} />
          {cv && (
            <div className="segmented">
              {(['all', 'missing', 'have'] as Show[]).map((key) => (
                <button key={key} className={show === key ? 'chosen' : ''} onClick={() => setShow(key)}>
                  {key === 'all' ? 'All' : key === 'missing' ? 'Not in your CV' : 'In your CV'}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <ul className="demand-list">
        {visible.map(({ skill, urls }) => {
          const inCv = cv?.includes(skill)
          const share = Math.round((100 * urls.length) / Math.max(counted.length, 1))
          return (
            <li key={skill}>
              <button className="demand-row" onClick={() => setOpen(open === skill ? null : skill)}>
                <span className="demand-name">{skill}</span>
                <span className="demand-track">
                  <span className="demand-bar" style={{ width: `${(100 * urls.length) / most}%` }} />
                </span>
                <span className="demand-count">{share}% · {urls.length} jobs</span>
                {cv && <span className={`chip ${inCv ? 'yes' : 'no'}`}>{inCv ? 'In your CV' : 'Not in your CV'}</span>}
              </button>
              {open === skill && (
                <ul className="demand-jobs">
                  {urls.map((url) => byUrl.get(url)).filter((job): job is Job => !!job).map((job) => (
                    <li key={job.url}>
                      <button className="link-button" onClick={() => onOpen(job)}>
                        {job.title}
                      </button>
                      <span className="muted"> · {job.company}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          )
        })}
      </ul>
      {visible.length === 0 && <p className="empty">No skills to show here.</p>}
    </section>
  )
}
