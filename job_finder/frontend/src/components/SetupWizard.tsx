import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type {
  ConnectionsAnswer, CvInfo, Preferences, PreferencesAnswer, Scorer, Suggestions,
} from '../api/types'
import { ConnectionForm } from './ConnectionForm'
import { CvDropZone } from './CvDropZone'
import { PreferencesForm } from './PreferencesForm'

type Props = {
  connections: ConnectionsAnswer
  preferences: PreferencesAnswer // the defaults to start from
  cv: CvInfo | null
  scorer: Scorer | null
  onConnections: (answer: ConnectionsAnswer) => void // after adding an AI
  onCv: () => void // after a CV upload: the page reloads its status
  onFinished: (saved: Preferences) => void // preferences saved: start downloading jobs
}

const STEPS = ['Choose an AI', 'Your CV', 'What you want']
const CLAUDE_CODE = { name: 'Claude Code', kind: 'claude' } as const

const errorText = (problem: unknown) =>
  problem instanceof ApiError ? problem.message : 'That did not work.'

// The first thing a new user sees: three short steps, then the jobs download.
// Each step reuses a piece of Settings, so nothing is built twice.
export function SetupWizard(props: Props) {
  const { connections, preferences, cv, scorer, onConnections, onCv, onFinished } = props
  const [step, setStep] = useState(connections.connections.length ? 1 : 0)
  const [otherWays, setOtherWays] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestions | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  async function work(what: string, action: () => Promise<void>) {
    setError('')
    setBusy(what)
    try {
      await action()
    } catch (problem) {
      setError(errorText(problem))
    } finally {
      setBusy('')
    }
  }

  // Claude Code in one click: is it installed, does it answer, then save it.
  const useClaudeCode = () => work('Checking Claude Code on this PC…', async () => {
    const found = await api.detectLocal('claude')
    if (!found.claude) {
      setError('Claude Code isn\'t installed on this PC. Install it and sign in, or choose another way.')
      return
    }
    setBusy('Checking Claude Code answers (one tiny request)…')
    const test = await api.testConnection({ fields: CLAUDE_CODE })
    if (!test.ok) {
      setError(`Claude Code didn't answer: ${test.error}`)
      return
    }
    onConnections(await api.addConnection(CLAUDE_CODE, ''))
    setStep(1)
  })

  // A CV: upload it, then the AI (if any) suggests what to look for.
  const upload = (file: File) => work('Reading your CV…', async () => {
    await api.uploadCv(file)
    onCv()
    if (scorer) {
      setBusy(`${scorer.name} is reading your CV…`)
      setSuggestions(await api.suggestFromCv())
    }
    setStep(2)
  })

  return (
    <main className="setup">
      <h2>Welcome to Job Finder</h2>
      <ol className="setup-steps">
        {STEPS.map((title, index) => (
          <li key={title} className={index === step ? 'current' : index < step ? 'done' : ''}>
            {title}
          </li>
        ))}
      </ol>
      {error && <p className="message error">{error}</p>}
      {busy && <p className="progress">{busy}</p>}

      {step === 0 && !busy && (
        <section className="settings-section setup-choice">
          <h3>Which AI should score how well jobs fit your CV?</h3>
          <div className="big-choices">
            <button className="big-choice" onClick={useClaudeCode}>
              <strong>Claude Code</strong>
              <span>If you have it. Uses your Claude plan.</span>
            </button>
            <button className="big-choice" onClick={() => setStep(1)}>
              <strong>Not now</strong>
              <span>Filter and track jobs; add an AI later in Settings.</span>
            </button>
          </div>
          {!otherWays ? (
            <button className="link-button" onClick={() => setOtherWays(true)}>
              Other ways: an API key, or a model on this PC
            </button>
          ) : (
            <ConnectionForm info={connections} editing={null} showName={false}
              ways={['service', 'local']}
              onSaved={(answer) => { onConnections(answer); setStep(1) }}
              onCancel={() => setOtherWays(false)} />
          )}
        </section>
      )}

      {step === 1 && !busy && (
        <section className="settings-section">
          <h3>Your CV <span className="muted small">· stays on this computer</span></h3>
          <CvDropZone cv={cv} onUpload={upload} onYears={() => {}} />
          <div className="form-actions">
            <button className="button secondary" onClick={() => setStep(0)}>← Back</button>
            <button className="link-button" onClick={() => setStep(2)}>
              {cv ? 'Keep this CV' : 'Skip for now'}
            </button>
          </div>
        </section>
      )}

      {step === 2 && (
        <PreferencesForm saveLabel="Save and download jobs" onSaved={onFinished}
          answer={suggestions ? { ...preferences, preferences: suggestions.preferences } : preferences}
          note={suggestions && <SuggestionSummary suggestions={suggestions} />} />
      )}
    </main>
  )
}

// What the AI read from the CV, in one line plus the roles as tags.
function SuggestionSummary({ suggestions }: { suggestions: Suggestions }) {
  const { professional_years: years, roles } = suggestions
  return (
    <div className="suggestion-summary">
      <p>
        <strong>From your CV</strong> · {years} year{years === 1 ? '' : 's'} of work
        {' '}· pre-filled below, change anything
      </p>
      {roles.length > 0 && (
        <p className="tags">{roles.map((role) => <span key={role} className="tag">{role}</span>)}</p>
      )}
    </div>
  )
}
