import { useEffect, useRef, useState } from 'react'
import { type Question, setConfirmHost } from '../logic/confirm'

// The app's own "are you sure?" box; logic/confirm.ts asks the questions. It's
// a <dialog>: Escape and Cancel answer "no", and the rest of the page can't be
// clicked while it's open.
export function ConfirmHost() {
  const [question, setQuestion] = useState<Question | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    setConfirmHost(setQuestion)
    return () => setConfirmHost(null)
  }, [])

  useEffect(() => {
    if (question) dialog.current?.showModal()
  }, [question])

  function reply(yes: boolean) {
    dialog.current?.close()
    question?.answer(yes)
    setQuestion(null)
  }

  return (
    <dialog ref={dialog} className="confirm-dialog" aria-labelledby="confirm-title"
      onCancel={(event) => { event.preventDefault(); reply(false) }}>
      {question && (
        <>
          <h2 id="confirm-title">{question.title}</h2>
          {question.text && <p className="muted">{question.text}</p>}
          <div className="confirm-buttons">
            {/* For what can't be undone, Cancel has the focus, so Enter doesn't delete. */}
            <button className="button secondary" autoFocus={question.danger}
              onClick={() => reply(false)}>Cancel</button>
            <button className={question.danger ? 'button danger' : 'button'} autoFocus={!question.danger}
              onClick={() => reply(true)}>
              {question.confirm}
            </button>
          </div>
        </>
      )}
    </dialog>
  )
}
