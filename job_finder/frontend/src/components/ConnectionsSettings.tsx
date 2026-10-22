import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type { Connection, ConnectionsAnswer } from '../api/types'
import { ConnectionForm } from './ConnectionForm'

type Props = {
  info: ConnectionsAnswer
  onChange: (answer: ConnectionsAnswer) => void // after any change, with the new list
}

// Settings → AI connections: the AIs you added, which one is in use, and
// adding, changing, switching and removing them.
export function ConnectionsSettings({ info, onChange }: Props) {
  // null: just the list; 'new': the add form; a connection: editing it.
  const [form, setForm] = useState<'new' | Connection | null>(info.connections.length ? null : 'new')
  const [error, setError] = useState('')

  async function act(action: () => Promise<ConnectionsAnswer>) {
    setError('')
    try {
      onChange(await action())
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'That did not work.')
    }
  }

  function remove(connection: Connection) {
    const ok = window.confirm(`Remove "${connection.name}"? Its key is deleted from your ` +
      "password safe. Scores it made are kept.")
    if (ok) act(() => api.removeConnection(connection.id))
  }

  return (
    <section className="settings-section">
      <h2>AI connections</h2>
      <p className="muted">The AIs that can score jobs. Add as many as you like and switch
        whenever you want: scores they made stay valid.</p>
      {error && <p className="message error">{error}</p>}

      {info.connections.length > 0 && (
        <ul className="connections">
          {info.connections.map((connection) => {
            const inUse = connection.id === info.active
            return (
              <li key={connection.id} className={inUse ? 'in-use' : undefined}>
                <div>
                  <strong>{connection.name}</strong>
                  {inUse && <span className="badge junior">In use</span>}
                  <span className="muted small">
                    {/* The kind, unless the name already says it ("Claude Code"). */}
                    {info.kinds[connection.kind] !== connection.name && ` ${info.kinds[connection.kind]}`}
                    {connection.model && ` · ${connection.model}`}
                    {connection.key_hint && ` · key ${connection.key_hint}`}
                  </span>
                </div>
                <div className="connection-actions">
                  {!inUse && (
                    <button className="button secondary"
                      onClick={() => act(() => api.useConnection(connection.id))}>Use</button>
                  )}
                  <button className="button secondary" onClick={() => setForm(connection)}>Change</button>
                  <button className="button secondary" onClick={() => remove(connection)}>Remove</button>
                </div>
              </li>
            )
          })}
        </ul>
      )}

      {form ? (
        <ConnectionForm key={form === 'new' ? 'new' : form.id} info={info}
          editing={form === 'new' ? null : form}
          onSaved={(answer) => { onChange(answer); setForm(null) }}
          onCancel={() => setForm(null)} />
      ) : (
        <button className="button" onClick={() => setForm('new')}>+ Add a connection</button>
      )}
    </section>
  )
}
