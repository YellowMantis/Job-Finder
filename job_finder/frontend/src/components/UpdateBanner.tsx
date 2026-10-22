import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type { AppUpdate } from '../api/types'

type Props = { current: string; update: AppUpdate }

// "A new version is available": what's new, and the choice to update now or later.
export function UpdateBanner({ current, update }: Props) {
  const [hidden, setHidden] = useState(false)
  const [state, setState] = useState<'offer' | 'working' | 'closing' | 'opened'>('offer')
  const [error, setError] = useState('')

  async function updateNow() {
    setState('working')
    setError('')
    try {
      const { closing } = await api.updateApp()
      setState(closing ? 'closing' : 'opened')
    } catch (problem) {
      setState('offer')
      setError(problem instanceof ApiError ? problem.message : 'The update did not start.')
    }
  }

  if (hidden) return null
  return (
    <section className="update-banner">
      {state === 'closing' ? (
        <p><strong>Installing Job Finder {update.version}…</strong> This window closes now; the
          installer will offer to open the new version when it's done.</p>
      ) : state === 'opened' ? (
        <p>The download page for Job Finder {update.version} opened in your browser.</p>
      ) : (
        <>
          <p>
            <strong>Job Finder {update.version} is available</strong>
            <span className="muted"> (you have {current}). Your data stays as it is.</span>
          </p>
          {update.notes && (
            <details>
              <summary>What's new</summary>
              <pre className="release-notes">{update.notes}</pre>
            </details>
          )}
          {error && <p className="error-text">{error}</p>}
          <div className="form-actions">
            <button className="button" onClick={updateNow} disabled={state === 'working'}>
              {state === 'working' ? 'Downloading…' : 'Update now'}
            </button>
            <button className="button secondary" onClick={() => setHidden(true)}>Later</button>
          </div>
        </>
      )}
    </section>
  )
}
