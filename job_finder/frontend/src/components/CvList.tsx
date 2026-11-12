import type { SavedCv } from '../api/types'

type Props = {
  cvs: SavedCv[]
  inUse: string | null // the id of the CV in use
  onUse: (cv: SavedCv) => void
  onDelete: (cv: SavedCv, withScores: boolean) => void
}

// Settings → Your CVs: every CV you uploaded, to switch to or take off the
// list. Taking one off keeps its scores (they come back if you upload it
// again); deleting it with its scores leaves nothing of it on this computer.
export function CvList({ cvs, inUse, onUse, onDelete }: Props) {
  function remove(cv: SavedCv) {
    const ok = window.confirm(`Remove "${cv.name}" from your list? Its scores are kept, ` +
      'and come back if you upload the same CV again.')
    if (ok) onDelete(cv, false)
  }

  function deleteAll(cv: SavedCv) {
    const ok = window.confirm(`Delete "${cv.name}" and every score made for it from this ` +
      'computer? This cannot be undone.')
    if (ok) onDelete(cv, true)
  }

  return (
    <section className="settings-section">
      <h2>Your CVs</h2>
      <p className="muted">Every CV you upload is kept here, so you can switch between them.
        Each keeps its own scores.</p>
      {cvs.length === 0 ? <p className="muted">No CV yet: drop one on the positions page.</p> : (
        <ul className="connections">
          {cvs.map((cv) => {
            const current = cv.id === inUse
            return (
              <li key={cv.id} className={current ? 'in-use' : undefined}>
                <div>
                  <strong>{cv.name}</strong>
                  {current && <span className="badge junior">In use</span>}
                  <span className="muted small"> · uploaded {cv.uploaded}</span>
                </div>
                <div className="connection-actions">
                  {!current && <button className="button secondary" onClick={() => onUse(cv)}>Use</button>}
                  <button className="button secondary" onClick={() => remove(cv)}>Remove from list</button>
                  <button className="button secondary danger" onClick={() => deleteAll(cv)}>
                    Delete with its scores
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
