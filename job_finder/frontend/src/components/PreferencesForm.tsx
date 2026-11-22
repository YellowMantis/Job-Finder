import { useState, type ReactNode } from 'react'
import { ApiError, api } from '../api/client'
import type { Preferences, PreferencesAnswer } from '../api/types'
import { CheckboxList } from './CheckboxList'
import { HomePicker } from './HomePicker'
import { InfoTip } from './InfoTip'

type Props = {
  answer: PreferencesAnswer // your preferences (or suggested ones) and the choices on offer
  onSaved: (preferences: Preferences) => void
  saveLabel?: string // the setup says "Save and download jobs"
  note?: ReactNode // shown at the top, e.g. what was suggested from your CV
}

const LEVEL_LABELS: Record<string, string> = {
  junior: 'Junior', 'not stated': 'Level not stated', senior: 'Senior',
}
const AGES = [{ days: 7, label: '7 days' }, { days: 14, label: '14 days' },
  { days: 30, label: '30 days' }, { days: 60, label: '60 days' }, { days: 0, label: 'any age' }]
const YEARS = [0, 1, 2, 3, 4, 5, 7, 10]

// What you're looking for: home, levels, fields, posting age, years of
// experience, industries to hide. Used in Settings and in the first-run setup.
export function PreferencesForm({ answer, onSaved, saveLabel = 'Save preferences', note }: Props) {
  const [draft, setDraft] = useState<Preferences>(answer.preferences)
  const [moreOptions, setMoreOptions] = useState(draft.hide_industries.length > 0)
  const [status, setStatus] = useState<{ text: string; isError: boolean } | null>(null)
  const change = (changes: Partial<Preferences>) => {
    setDraft((current) => ({ ...current, ...changes }))
    setStatus(null)
  }

  async function save() {
    try {
      onSaved(await api.savePreferences(draft))
      setStatus({ text: 'Saved. The positions now follow these preferences.', isError: false })
    } catch (problem) {
      setStatus({ text: problem instanceof ApiError ? problem.message : 'Not saved.', isError: true })
    }
  }

  return (
    <section className="settings-section preferences">
      <h2>Your preferences</h2>
      <p className="muted">Saved on this computer only. Postings that don't match your
        preferences are hidden, not deleted, and come back if you change them.</p>
      {note}

      <h3>Where you live <InfoTip>Distances to jobs are measured from this place.</InfoTip></h3>
      <HomePicker home={draft.home} onChoose={(home) => change({ home })} />

      <h3>Levels to show</h3>
      <CheckboxList selected={draft.levels} onChange={(levels) => change({ levels })}
        options={answer.levels.map((level) => ({ value: level, label: LEVEL_LABELS[level] ?? level }))} />

      <h3>
        Fields you're interested in{' '}
        <InfoTip>Only these fields appear in the table. Saving downloads the full posting
          texts for them, so years and work mode can be shown.</InfoTip>
      </h3>
      <CheckboxList selected={draft.fields} onChange={(fields) => change({ fields })}
        options={answer.fields.map((field) => ({ value: field }))} />

      <h3>Posted within</h3>
      <select value={draft.max_age_days}
        onChange={(event) => change({ max_age_days: Number(event.target.value) })}>
        {AGES.map(({ days, label }) => <option key={days} value={days}>{label}</option>)}
      </select>

      <h3>
        Most years of experience asked{' '}
        <InfoTip>Postings that ask for more are hidden. The years are read from the
          posting text.</InfoTip>
      </h3>
      <select value={draft.max_years ?? ''}
        onChange={(event) => change({
          max_years: event.target.value === '' ? null : Number(event.target.value),
        })}>
        <option value="">no limit</option>
        {YEARS.map((years) => (
          <option key={years} value={years}>{years === 0 ? 'none (entry level)' : `${years} years`}</option>
        ))}
      </select>
      {draft.max_years !== null && (
        <label className="checkbox">
          <input type="checkbox" checked={draft.keep_unknown_years}
            onChange={(event) => change({ keep_unknown_years: event.target.checked })} />
          {' '}Keep postings that don't say
        </label>
      )}

      <h3>
        <button type="button" className="link-button" onClick={() => setMoreOptions(!moreOptions)}>
          {moreOptions ? '▾' : '▸'} Industries to hide (optional)
        </button>
      </h3>
      {moreOptions && (
        <CheckboxList selected={draft.hide_industries}
          onChange={(hide_industries) => change({ hide_industries })}
          options={Object.entries(answer.industries).map(([value, label]) => ({ value, label }))} />
      )}

      {status && <p className={`message${status.isError ? ' error' : ''}`}>{status.text}</p>}
      <div className="form-actions">
        <button className="button" onClick={save} disabled={!draft.home}>{saveLabel}</button>
        {!draft.home && <span className="muted small">Choose where you live first.</span>}
      </div>
    </section>
  )
}
