import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api/client'
import type { CvInfo } from '../api/types'

type Props = {
  cv: CvInfo | null
  onUpload: (file: File) => void
  onYears: (years: number) => void
}

// The box to drop (or choose) your CV in, with the years of paid work read
// from it, which you can correct.
export function CvDropZone({ cv, onUpload, onYears }: Props) {
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

  const classes = ['drop-zone', dragging && 'dragging', cv && 'loaded'].filter(Boolean).join(' ')
  return (
    <section className={classes} onClick={() => fileInput.current?.click()}
      onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)} onDrop={drop}>
      <input ref={fileInput} type="file" accept="application/pdf" hidden
        onChange={(event) => event.target.files?.[0] && onUpload(event.target.files[0])} />
      <p className="drop-title">{cv ? `CV loaded: ${cv.name}` : 'Drop your CV here'}</p>
      <p className="drop-hint">
        {cv
          ? `${cv.characters} characters read · uploaded ${cv.uploaded} · drop another PDF to replace it`
          : 'PDF only, or click to choose a file'}
      </p>
      {cv && (
        // Clicks in here must not open the file chooser.
        <label className="cv-years" onClick={(event) => event.stopPropagation()}>
          Years of paid work experience:
          {/* Saved when you leave the box, not on every keystroke. The key makes
              a newly uploaded CV start a fresh box with its own value. */}
          <input key={cv.uploaded} type="number" min={0} max={50} step={1}
            defaultValue={cv.professional_years ?? ''}
            onBlur={(event) => {
              const years = Number(event.target.value)
              if (event.target.value !== '' && Number.isInteger(years) && years >= 0) onYears(years)
            }} />
        </label>
      )}
      {cv && (
        <div className="cv-sent" onClick={(event) => event.stopPropagation()}>
          <span className="drop-hint">
            Your name, contact details and links are removed before your CV is sent to an AI.{' '}
            <button className="link-button" onClick={showSent}>
              {sent === null ? 'See what the AI receives' : 'Hide it'}
            </button>
          </span>
          {sent !== null && <pre className="cv-sent-text">{sent}</pre>}
        </div>
      )}
    </section>
  )
}
