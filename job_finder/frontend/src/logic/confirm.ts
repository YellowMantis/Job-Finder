// Asking before something that uses your AI allowance or can't be undone, in
// the app's own look (the browser's confirm box says "127.0.0.1:63536 says").
//
//   if (!(await confirmAction({ title: 'Delete it?', confirm: 'Delete', danger: true }))) return
//
// <ConfirmHost /> (components/ConfirmDialog.tsx) is placed once in App and draws
// the question; confirmAction can then be called from anywhere.

export type ConfirmOptions = {
  title: string
  text?: string
  confirm: string // what the button does: "Score 3 jobs", "Delete"
  danger?: boolean // red button, for what can't be undone
}

export type Question = ConfirmOptions & { answer: (yes: boolean) => void }

let show: ((question: Question) => void) | null = null

// Called by ConfirmHost when it appears (with its way of showing a question)
// and when it goes (with null).
export function setConfirmHost(host: ((question: Question) => void) | null) {
  show = host
}

export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  return new Promise((answer) => {
    if (show) show({ ...options, answer })
    else answer(window.confirm(`${options.title}\n\n${options.text ?? ''}`)) // no host: fall back
  })
}
