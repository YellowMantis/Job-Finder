// Every request the page makes to the back end goes through this file, so
// addresses, error handling and (later) caching live in one place.

import type {
  BatchRecord, ConnectionFields, ConnectionsAnswer, ConnectionTarget, CvInfo, DetectAnswer,
  FitProgress, HiddenJob, JobsAnswer, Place, Preferences, PreferencesAnswer, Status, Suggestions,
  TestAnswer, UpdateProgress,
} from './types'

// The back end answered with an error; message is its explanation.
export class ApiError extends Error {}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options)
  const body = await response.json()
  if (!response.ok) throw new ApiError(body.error ?? `Request failed: ${path}`)
  return body as T
}

function post<T>(path: string, data: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export const api = {
  status: () => request<Status>('/api/status'),
  jobs: () => request<JobsAnswer>('/api/jobs'),
  hidden: () => request<HiddenJob[]>('/api/hidden'),
  // One job's posting text, fetched when its side panel opens.
  posting: (url: string) =>
    request<{ text: string }>(`/api/posting?url=${encodeURIComponent(url)}`),
  // Mark or unmark "I applied"; answers with the saved date, or null.
  setApplied: (url: string, applied: boolean) =>
    post<{ applied: string | null }>('/api/applied', { url, applied }),
  // Send a CV PDF; the back end checks it is a PDF and reads its text.
  uploadCv: (file: File) => {
    const form = new FormData()
    form.append('cv', file)
    return request<CvInfo>('/api/cv', { method: 'POST', body: form })
  },
  // Suggest preferences from the loaded CV, with the AI connection in use.
  suggestFromCv: () => post<Suggestions>('/api/cv/suggest', {}),
  // Correct the years of paid work read from the CV.
  setYears: (years: number) => post<CvInfo>('/api/cv/years', { years }),
  // The CV exactly as an AI receives it: without your name and contact details.
  cvSent: () => request<{ text: string }>('/api/cv/sent'),

  // Scoring runs in the background: start it, ask how it's going, stop it.
  // again: also redo jobs that already have a score (for example with another AI).
  startFit: (urls: string[], again = false) =>
    post<FitProgress>('/api/fit/start', { urls, again }),
  fitStatus: () => request<FitProgress>('/api/fit/status'),
  stopFit: () => post<FitProgress>('/api/fit/stop', {}),
  fitLog: () => request<BatchRecord[]>('/api/fit/log'),

  // So does updating the listings.
  startUpdate: () => post<UpdateProgress>('/api/update', {}),
  updateStatus: () => request<UpdateProgress>('/api/update/status'),

  // AI connections. Keys are sent once, when saved, and never come back.
  connections: () => request<ConnectionsAnswer>('/api/connections'),
  addConnection: (fields: ConnectionFields, key: string) =>
    post<ConnectionsAnswer>('/api/connections', { fields, key }),
  // key undefined keeps the saved key.
  updateConnection: (id: string, fields: ConnectionFields, key?: string) =>
    post<ConnectionsAnswer>(`/api/connections/${id}`, { fields, key }),
  removeConnection: (id: string) =>
    request<ConnectionsAnswer>(`/api/connections/${id}`, { method: 'DELETE' }),
  useConnection: (id: string) => post<ConnectionsAnswer>(`/api/connections/${id}/activate`, {}),
  // The session % that Claude Code's /usage shows now, to estimate later batches.
  calibrate: (id: string, percent: number) =>
    post<ConnectionsAnswer>(`/api/connections/${id}/calibrate`, { percent }),
  connectionModels: (target: ConnectionTarget) =>
    post<{ models: string[] }>('/api/connections/models', target),
  testConnection: (target: ConnectionTarget) => post<TestAnswer>('/api/connections/test', target),
  // Look on this PC, only when you ask, only for what you ask: Claude Code, or
  // Ollama and LM Studio.
  detectLocal: (what: 'claude' | 'local') =>
    post<DetectAnswer>('/api/connections/detect', { what }),

  // Install the newer version you chose; on Windows the app then closes.
  updateApp: () => post<{ closing: boolean }>('/api/update-app', {}),

  // Your preferences, and towns to choose your home from.
  preferences: () => request<PreferencesAnswer>('/api/preferences'),
  savePreferences: (preferences: Preferences) =>
    post<Preferences>('/api/preferences', preferences),
  places: (query: string) => request<Place[]>(`/api/places?q=${encodeURIComponent(query)}`),
}
