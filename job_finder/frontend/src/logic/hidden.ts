import type { HiddenJob } from '../api/types'

// The hidden jobs whose position, company or reason contains what was typed,
// whatever its letter case. Nothing typed: all of them.
export function matchingHidden(rows: HiddenJob[], search: string): HiddenJob[] {
  const typed = search.trim().toLowerCase()
  if (!typed) return rows
  return rows.filter((row) => `${row.title} ${row.company} ${row.reason}`.toLowerCase().includes(typed))
}
