import { useEffect, useState } from 'react'

// Data for a tab that stays on the page while hidden. It is fetched when the
// tab is shown and the data has changed since (version), never while hidden:
// switching back to the tab is instant, and a scoring run's many reloads cost
// nothing until you look. While a newer copy loads, the last one stays shown.
// setData changes the copy in hand, e.g. to drop a row at once.
export function useLoadedWhenShown<T>(load: () => Promise<T>, shown: boolean, version: string) {
  const [loaded, setLoaded] = useState<{ version: string; data: T } | null>(null)

  useEffect(() => {
    if (!shown || loaded?.version === version) return
    let current = true // an answer that arrives after a newer request is ignored
    load().then((data) => current && setLoaded({ version, data })).catch(() => {})
    return () => { current = false }
  }, [load, shown, version, loaded?.version])

  const setData = (change: (data: T) => T) =>
    setLoaded((now) => now && { ...now, data: change(now.data) })
  return [loaded?.data ?? null, setData] as const
}
