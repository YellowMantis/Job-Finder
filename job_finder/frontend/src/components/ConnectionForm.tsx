import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type { Connection, ConnectionsAnswer, DetectAnswer, TestAnswer } from '../api/types'
import {
  draftOf, emptyDraft, fieldsOf, needsKey, suggestedName, type Draft, type LocalChoice, type Way,
} from '../logic/connections'

type Props = {
  info: ConnectionsAnswer // for the list of services
  editing: Connection | null // null: adding a new one
  onSaved: (answer: ConnectionsAnswer) => void
  onCancel: () => void
  showName?: boolean // the first-run setup names the connection itself
  ways?: Way[] // which ways to offer (the setup offers Claude Code separately)
}

const WAYS: { way: Way; title: string; hint: string }[] = [
  { way: 'claude', title: 'Claude Code', hint: 'Uses your Claude plan. Reads postings most carefully.' },
  { way: 'service', title: 'An AI service with your key',
    hint: 'OpenAI, Groq, OpenRouter… Some have free tiers. Pick a large model.' },
  { way: 'local', title: 'A model on this PC',
    hint: 'Ollama or LM Studio. Free and private, but small models score less accurately.' },
]

const errorText = (problem: unknown, fallback: string) =>
  problem instanceof ApiError ? problem.message : fallback

// Add (or change) one AI connection: choose how to reach the AI, choose a
// model from the service's own list, save it (which tests it first).
export function ConnectionForm(props: Props) {
  const { info, editing, onSaved, onCancel, showName = true } = props
  const ways = WAYS.filter(({ way }) => (props.ways ?? ['claude', 'service', 'local']).includes(way))
  const [draft, setDraft] = useState<Draft>(
    editing ? draftOf(editing) : { ...emptyDraft, way: ways[0].way })
  const [name, setName] = useState(editing?.name ?? '') // '' means "use the suggestion"
  const [key, setKey] = useState('') // '' when editing means "keep the saved key"
  const [models, setModels] = useState<string[] | null>(null) // the service's list, once loaded
  const [found, setFound] = useState<DetectAnswer | null>(null) // what "look on this PC" found
  const [test, setTest] = useState<TestAnswer | null>(null)
  const [busy, setBusy] = useState('') // what is being done right now, for the buttons
  const [error, setError] = useState('')

  const finalName = name.trim() || suggestedName(draft, info.services)
  const fields = fieldsOf(draft, finalName)
  // Requests about this connection: the saved key is used unless a new one is typed.
  const target = { ...(editing ? { id: editing.id } : {}), fields, ...(key ? { key } : {}) }

  // Any change to what is chosen makes an earlier test result meaningless.
  function change(changes: Partial<Draft>) {
    setDraft((current) => ({ ...current, ...changes }))
    setTest(null)
    setError('')
  }

  async function run(what: string, action: () => Promise<void>) {
    setBusy(what)
    setError('')
    try {
      await action()
    } catch (problem) {
      setError(errorText(problem, 'That did not work.'))
    } finally {
      setBusy('')
    }
  }

  const lookFor = (what: 'claude' | 'local') =>
    run('look', async () => setFound(await api.detectLocal(what)))
  const loadModels = () => run('models', async () => {
    const { models } = await api.connectionModels(target)
    setModels(models)
    if (models.length && !models.includes(draft.model)) change({ model: models[0] })
  })
  // Saving tests the connection first (one tiny request), so you only keep one
  // that works. If the test fails, you see why, and can still save it anyway.
  const store = async () => onSaved(editing
    ? await api.updateConnection(editing.id, fields, key || undefined)
    : await api.addConnection(fields, key))
  const save = () => run('save', async () => {
    const result = await api.testConnection(target)
    setTest(result)
    if (result.ok) await store()
  })
  const saveAnyway = () => run('save', store)

  const missingKey = needsKey(draft, editing) && !key
  const missingModel = draft.way !== 'claude' &&
    !(draft.way === 'local' ? draft.local?.model : draft.model)

  return (
    <section className="connection-form">
      <h3>{editing ? `Change "${editing.name}"` : 'Add an AI connection'}</h3>

      <fieldset className="ways">
        <legend>How should the AI be reached?</legend>
        {ways.map(({ way, title, hint }) => (
          <label key={way} className={`way${draft.way === way ? ' chosen' : ''}`}>
            <input type="radio" name="way" checked={draft.way === way}
              onChange={() => change({ way })} />
            <span><strong>{title}</strong><span className="muted small">{hint}</span></span>
          </label>
        ))}
      </fieldset>

      {draft.way === 'claude' && (
        <div className="form-step">
          <button className="button secondary" onClick={() => lookFor('claude')} disabled={busy !== ''}>
            {busy === 'look' ? 'Looking…' : 'Check this PC for Claude Code'}
          </button>
          {found && (found.claude
            ? <span className="good">✓ Claude Code is installed.</span>
            : <span className="error-text">Not found. Install Claude Code and sign in first.</span>)}
          <p className="muted small">The check only looks for the program on this computer and
            sends nothing anywhere.</p>
        </div>
      )}

      {draft.way === 'service' && (
        <div className="form-step form-grid">
          <label>Service
            <select value={draft.service}
              onChange={(event) => { setModels(null); change({ service: event.target.value, model: '' }) }}>
              {Object.entries(info.services).filter(([id]) => id !== 'lmstudio')
                .map(([id, label]) => <option key={id} value={id}>{label}</option>)}
              <option value="custom">Another service (enter its address)</option>
            </select>
          </label>
          {draft.service === 'custom' && (
            <label>Address
              <input type="url" placeholder="https://…/v1" value={draft.baseUrl}
                onChange={(event) => change({ baseUrl: event.target.value })} />
            </label>
          )}
          <label>API key
            <input type="password" autoComplete="off" value={key}
              placeholder={editing?.key_hint ? `saved (${editing.key_hint}); leave empty to keep it` : 'paste your key'}
              onChange={(event) => { setKey(event.target.value); setTest(null) }} />
          </label>
          <label>Model
            <span className="inline">
              {models && models.length > 0 ? (
                <select value={draft.model} onChange={(event) => change({ model: event.target.value })}>
                  {models.map((model) => <option key={model}>{model}</option>)}
                </select>
              ) : (
                <input placeholder="load the list, or type a name" value={draft.model}
                  onChange={(event) => change({ model: event.target.value })} />
              )}
              <button className="button secondary" onClick={loadModels}
                disabled={busy !== '' || missingKey}>
                {busy === 'models' ? 'Loading…' : 'Load models'}
              </button>
            </span>
          </label>
          <p className="muted small">Your key is kept in your computer's password safe and sent
            only to this service.</p>
        </div>
      )}

      {draft.way === 'local' && (
        <div className="form-step">
          <button className="button secondary" onClick={() => lookFor('local')} disabled={busy !== ''}>
            {busy === 'look' ? 'Looking…' : 'Look for Ollama and LM Studio on this PC'}
          </button>
          <p className="muted small">Checks only whether they are running on this computer;
            nothing is sent anywhere.</p>
          {found && <LocalModels found={found} chosen={draft.local}
            onChoose={(local) => change({ local })} />}
          {!found && draft.local && <p>Chosen: {suggestedName(draft, info.services)}</p>}
        </div>
      )}

      {showName && (
        <label className="form-step">Name (how it appears in "Score with")
          <input value={name} placeholder={suggestedName(draft, info.services)}
            onChange={(event) => setName(event.target.value)} />
        </label>
      )}

      {error && <p className="message error">{error}</p>}
      {test && !test.ok && (
        <p className="message error">It didn't answer: {test.error}{' '}
          <button className="link-button" onClick={saveAnyway}>Save anyway</button></p>
      )}

      <div className="form-actions">
        <button className="button" onClick={save} disabled={busy !== '' || missingKey || missingModel}
          title="Checks it works first, with one tiny request (about 5,000 tokens for Claude Code)">
          {busy === 'save' ? 'Checking it works…' : editing ? 'Save changes' : 'Save and use it'}
        </button>
        <button className="button secondary" onClick={onCancel}>Cancel</button>
      </div>
    </section>
  )
}

// The models found on this PC, to pick one.
function LocalModels({ found, chosen, onChoose }: {
  found: DetectAnswer
  chosen: LocalChoice | null
  onChoose: (choice: LocalChoice) => void
}) {
  const choices: LocalChoice[] = [
    ...(found.ollama ?? []).map((model) => ({ runner: 'ollama' as const, model })),
    ...(found.lmstudio ?? []).map((model) => ({ runner: 'lmstudio' as const, model })),
  ]
  if (!choices.length) {
    return <p className="error-text">Neither Ollama nor LM Studio is running (or has a model).
      Start one, download a model in it, and look again.</p>
  }
  return (
    <div className="checkbox-list">
      {choices.map((choice) => (
        <label key={`${choice.runner}:${choice.model}`}>
          <input type="radio" name="local-model"
            checked={chosen?.runner === choice.runner && chosen.model === choice.model}
            onChange={() => onChoose(choice)} />
          {' '}{choice.runner === 'ollama' ? 'Ollama' : 'LM Studio'}: {choice.model}
        </label>
      ))}
    </div>
  )
}
