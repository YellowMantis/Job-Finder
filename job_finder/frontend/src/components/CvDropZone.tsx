import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api/client'
import type { CvInfo, SavedCv } from '../api/types'

type Props = {
  cv: CvInfo | null
  onUpload: (file: File) => void
  onYears: (years: number) => void
  // Your saved CVs, to switch between (not during the first-run setup).
  saved?: { cvs: SavedCv[]; inUse: string | null; onUse: (cv: SavedCv) => void }
}

// The box to drop (or choose) your CV in, with the years of paid work read
// from it, which you can correct, and a choice of your saved CVs.
export function CvDropZone({ cv, onUpload, onYears, saved }: Props) {
  const [dragging, setDragging] = useState(false)
  const [sent, setSent] = useState<string | null>(null) // what the AI receives, once asked
  const fileInput = useRef<HTMLInputElement>(null)

  async function showSent() {
    if (sent !== null) return setSent(null) // the second click hides it again
    try {
      setSent((await api.cvSent()).text)
    } catch {
      setSent('Could not load it. Is the back end running?')
    }
  }

  function drop(event: DragEvent) {
    event.preventDefault() // stops the browser from opening the PDF itself
    setDragging(false)
    const file = event.dataTransfer.files[0]
    if (file) onUpload(file)
  }

  const dropHandlers = {
    onDragOver: (event: DragEvent) => { event.preventDefault(); setDragging(true) },
    onDragLeave: () => setDragging(false),
    onDrop: drop,
  }
  const chooser = (
    <input ref={fileInput} type="file" accept="application/pdf" hidden
      onChange={(event) => event.target.files?.[0] && onUpload(event.target.files[0])} />
  )

  // No CV yet: a big box to drop it in.
  if (!cv) {
    return (
      <section className={`drop-zone${dragging ? ' dragging' : ''}`}
        onClick={() => fileInput.current?.click()} {...dropHandlers}>
        {chooser}
        <p className="drop-title">Drop your CV here</p>
        <p className="drop-hint">PDF only, or click to choose a file</p>
      </section>
    )
  }

  // A CV loaded: one slim line, which still takes a new PDF dropped on it.
  return (
    <section className={`cv-bar${dragging ? ' dragging' : ''}`} {...dropHandlers}>
      {chooser}
      <div className="cv-bar-row">
        <span className="cv-name">
          {/* A small page with lines: "this is your CV". */}
          <span className="cv-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
              <path d="M14 3v5h5M9 13h6M9 17h6" />
            </svg>
          </span>
          <span className="cv-label">Your CV</span>
          {saved && saved.cvs.length > 1 ? (
            <select className="cv-choice" value={saved.inUse ?? ''} title="Switch to another saved CV"
              onChange={(event) => {
                const chosen = saved.cvs.find((c) => c.id === event.target.value)
                if (chosen) saved.onUse(chosen)
              }}>
              {saved.cvs.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          ) : <strong>{cv.name}</strong>}
        </span>
        <label className="cv-years">
          Years of paid work
          {/* Saved when you leave the box, not on every keystroke. The key makes
              a newly uploaded CV start a fresh box with its own value. */}
          <input key={cv.uploaded} type="number" min={0} max={50} step={1}
            defaultValue={cv.professional_years ?? ''}
            onBlur={(event) => {
              const years = Number(event.target.value)
              if (event.target.value !== '' && Number.isInteger(years) && years >= 0) onYears(years)
            }} />
        </label>
        <button className="link-button" onClick={showSent}
          title="Your name, contact details and links are removed before your CV is sent to an AI.">
          {sent === null ? 'See what the AI receives' : 'Hide it'}
        </button>
        <button className="button secondary cv-replace" onClick={() => fileInput.current?.click()}
          title="Or drop a PDF on this line. Your CVs are kept: switch or remove them in Settings.">
          Add a CV
        </button>
      </div>
      {sent !== null && <pre className="cv-sent-text">{sent}</pre>}
    </section>
  )
}
