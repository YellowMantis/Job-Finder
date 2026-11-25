import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api/client'
import type { CvInfo, SavedCv } from '../api/types'
import { Dropdown } from './Dropdown'

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
    // Moving over the box's own buttons also counts as leaving it: only a real exit does.
    onDragLeave: (event: DragEvent) => {
      if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false)
    },
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

  // A CV loaded: the left half of the bar, which still takes a new PDF dropped on it.
  const missingYears = cv.professional_years === undefined
  return (
    <div className={`cv-part${dragging ? ' dragging' : ''}`} {...dropHandlers}>
      {chooser}
      {/* A small page with lines: "this is your CV". */}
      <span className="cv-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
          strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5M9 13h6M9 17h6" />
        </svg>
      </span>
      {saved && saved.cvs.length > 1 ? (
        <Dropdown className="field cv-choice" value={saved.inUse ?? ''} label="Your CV"
          title="Your CV. Switch to another saved CV here."
          options={saved.cvs.map((c) => ({ value: c.id, label: c.name }))}
          onChange={(id) => {
            const chosen = saved.cvs.find((c) => c.id === id)
            if (chosen && id !== saved.inUse) saved.onUse(chosen)
          }} />
      ) : <strong className="cv-name" title="Your CV">{cv.name}</strong>}
      {/* Fit scores need it, so while it's empty the box is red and says so. */}
      <label className={`field cv-years${missingYears ? ' missing' : ''}`}
        title="Years of paid work, from your CV. Fit scores weigh it against the years a job asks for.">
        {/* Saved when you leave the box (or press Enter), not on every keystroke.
            The key makes a newly uploaded CV start a fresh box with its own value. */}
        <input key={cv.uploaded} id="cv-years" /* App points you here when you score without it */
          type="number" min={0} max={50} step={1} defaultValue={cv.professional_years ?? ''}
          placeholder="?" aria-label="Years of paid work"
          aria-invalid={missingYears} aria-describedby={missingYears ? 'cv-years-note' : undefined}
          onKeyDown={(event) => event.key === 'Enter' && event.currentTarget.blur()}
          onBlur={(event) => {
            const years = Number(event.target.value)
            if (event.target.value !== '' && Number.isInteger(years) && years >= 0) onYears(years)
          }} />
        <span>yrs exp</span>
      </label>
      {missingYears && <span id="cv-years-note" className="cv-years-note">needed for fit scores</span>}
      {/* Outlined, not filled: easy to find, but Score stays the one loud button in the bar. */}
      <button className="button secondary with-icon bar-button" onClick={() => fileInput.current?.click()}
        title="Or drop a PDF here. Your CVs are kept: switch between them here, or remove them in Settings.">
        {/* An arrow up out of a tray: "upload" */}
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 15V4M7 9l5-5 5 5M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" />
        </svg>
        Add CV
      </button>
      <button className="link-button" onClick={showSent}
        title="Your name, contact details and links are removed before your CV is sent to an AI.">
        {sent === null ? 'Preview AI input' : 'Hide AI input'}
      </button>
      {dragging && <div className="cv-drop-note">Drop the PDF to add it to your CVs</div>}
      {sent !== null && <pre className="cv-sent-text">{sent}</pre>}
    </div>
  )
}
