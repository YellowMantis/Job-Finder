import { useLayoutEffect, useRef, type RefObject } from 'react'

const GLIDE_MS = 450 // as .gliding in index.css
const MARGIN = 200 // rows this close to the screen glide too, so they don't pop in at the edge
const MAX_GLIDING = 40 // more rows than this moving at once: no animation (see below)

// Rows that change place glide from their old place to their new one, instead
// of jumping: when new scores re-sort the table, you can follow where a job
// went. The trick ("FLIP"): after React has moved the rows, each moved row is
// shifted back to where it was, then let go, so it slides into its new place.
//
// Only for re-orders of the same rows in the same sort (new data, like scores
// arriving): when you change the sort or a filter, `order` changes and the
// table simply redraws. Only rows on or near the screen move; rows far away
// just change place. Rows need data-url. Off when Windows reduces motion.
export function useRowGlide(body: RefObject<HTMLTableSectionElement | null>, order: string) {
  const before = useRef(new Map<string, number>()) // each row's top, relative to the table body
  const lastOrder = useRef(order)

  useLayoutEffect(() => {
    const tbody = body.current
    if (!tbody) return
    // Hidden (Settings is open): rows can't be measured, they'd all seem to be
    // at the top. Forget the old places, so coming back doesn't glide anything.
    if (tbody.offsetParent === null) {
      before.current = new Map()
      return
    }
    const bodyTop = tbody.getBoundingClientRect().top
    const rows = [...tbody.rows]
    const now = new Map(rows.map((row) => [row.dataset.url ?? '', row.getBoundingClientRect().top - bodyTop]))
    const previous = before.current
    before.current = now
    const sameTable = order === lastOrder.current
    lastOrder.current = order
    if (!sameTable || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const onScreen = (top: number) => bodyTop + top > -MARGIN && bodyTop + top < window.innerHeight + MARGIN
    const moved: HTMLTableRowElement[] = []
    for (const row of rows) {
      const from = previous.get(row.dataset.url ?? '')
      const to = now.get(row.dataset.url ?? '')
      if (from === undefined || to === undefined || from === to) continue
      if (onScreen(from) || onScreen(to)) moved.push(row)
    }
    // A re-sort moves the dozen or so rows on screen. Far more means something
    // else happened (the window resized, say): just show the new places.
    if (moved.length === 0 || moved.length > MAX_GLIDING) return
    for (const row of moved) {
      // Back to where it was, at once (no transition yet)...
      const shift = previous.get(row.dataset.url ?? '')! - now.get(row.dataset.url ?? '')!
      row.classList.add('gliding')
      row.style.transition = 'none'
      row.style.transform = `translateY(${shift}px)`
    }
    void tbody.offsetHeight // let the browser take in the old places before letting go
    // ...then let go: the transition in index.css slides each row home.
    requestAnimationFrame(() => {
      for (const row of moved) {
        row.style.transition = ''
        row.style.transform = ''
      }
    })
    // Each row drops its raised look once home. Its own timer: the table redraws
    // every few seconds while scoring, which mustn't cancel it, and a row that
    // starts a new glide replaces its old timer, so it isn't lowered mid-way.
    for (const row of moved) {
      clearTimeout(landing.get(row))
      landing.set(row, setTimeout(() => row.classList.remove('gliding'), GLIDE_MS + 50))
    }
  })
}

// The pending "drop the raised look" timer of each gliding row.
const landing = new WeakMap<HTMLTableRowElement, ReturnType<typeof setTimeout>>()
