import { useCallback, useEffect, useRef, useState } from 'react'
import type { Progress } from '../api/types'

// Follow a task that runs in the background on the back end (scoring, or
// updating the listings). While it runs, its status is asked for every two
// seconds; when it is idle, nothing is asked at all.
//
// onStep is called when something happened: the count of finished items went
// up, or the task stopped. That's when the page reloads its data, rather than
// on every check.
export function useProgress<T extends Progress>(
  fetchStatus: () => Promise<T>,
  onStep: (progress: T) => void,
) {
  const [progress, setProgress] = useState<T | null>(null)
  const previous = useRef<T | null>(null)
  // The latest onStep, without restarting the checks whenever App redraws.
  const onStepRef = useRef(onStep)
  useEffect(() => { onStepRef.current = onStep }, [onStep])

  // Take in a fresh status, and tell App if something happened since the last one.
  const receive = useCallback((next: T) => {
    const before = previous.current
    previous.current = next
    setProgress(next)
    if (before && (next.done !== before.done || (before.running && !next.running))) {
      onStepRef.current(next)
    }
  }, [])

  const check = useCallback(() => fetchStatus().then(receive), [fetchStatus, receive])

  // Once when the page opens: picks up a task that is already running.
  useEffect(() => {
    fetchStatus().then(receive).catch(() => {})
  }, [fetchStatus, receive])

  // While running, check again in two seconds.
  useEffect(() => {
    if (!progress?.running) return
    const timer = setTimeout(() => fetchStatus().then(receive).catch(() => {}), 2000)
    return () => clearTimeout(timer)
  }, [progress, fetchStatus, receive])

  return { progress, check }
}
