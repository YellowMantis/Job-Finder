// The rules of the "add an AI connection" form, as plain functions
// (tested in connections.test.ts).

import type { Connection, ConnectionFields } from '../api/types'

// The three ways the form offers. "This PC" covers both Ollama and LM Studio:
// for the user it's one idea, "a model on my computer".
export type Way = 'claude' | 'service' | 'local'

// Where a local model runs: Ollama, or LM Studio (which speaks the OpenAI format).
export type LocalChoice = { runner: 'ollama' | 'lmstudio'; model: string }

// Everything the form holds.
export type Draft = {
  way: Way
  service: string // for 'service': groq, openai, openrouter or custom
  baseUrl: string // for a custom service
  model: string
  local: LocalChoice | null
}

export const emptyDraft: Draft = {
  way: 'claude', service: 'anthropic', baseUrl: '', model: '', local: null,
}

// A saved connection, back in the form's terms (for editing it).
export function draftOf(connection: Connection): Draft {
  if (connection.kind === 'ollama') {
    return { ...emptyDraft, way: 'local', local: { runner: 'ollama', model: connection.model } }
  }
  if (connection.kind === 'api' && connection.service === 'lmstudio') {
    return { ...emptyDraft, way: 'local', local: { runner: 'lmstudio', model: connection.model } }
  }
  if (connection.kind === 'anthropic') {
    return { ...emptyDraft, way: 'service', service: 'anthropic', model: connection.model }
  }
  if (connection.kind === 'api') {
    return { ...emptyDraft, way: 'service', service: connection.service,
      baseUrl: connection.base_url, model: connection.model }
  }
  return { ...emptyDraft, way: 'claude' }
}

// What the back end needs (connections.check), from the form.
export function fieldsOf(draft: Draft, name: string): ConnectionFields {
  if (draft.way === 'claude') return { name, kind: 'claude' }
  if (draft.way === 'local') {
    const local = draft.local ?? { runner: 'ollama', model: '' }
    return local.runner === 'ollama'
      ? { name, kind: 'ollama', model: local.model }
      : { name, kind: 'api', service: 'lmstudio', model: local.model }
  }
  if (draft.service === 'anthropic') return { name, kind: 'anthropic', model: draft.model }
  return { name, kind: 'api', service: draft.service, model: draft.model,
    ...(draft.service === 'custom' ? { base_url: draft.baseUrl } : {}) }
}

// A name to start from, e.g. "Groq: llama-3.3-70b"; you can change it.
export function suggestedName(draft: Draft, services: Record<string, string>) {
  if (draft.way === 'claude') return 'Claude Code'
  if (draft.way === 'local') {
    if (!draft.local) return 'A model on this PC'
    const runner = draft.local.runner === 'ollama' ? 'Ollama' : 'LM Studio'
    return draft.local.model ? `${runner}: ${draft.local.model}` : runner
  }
  const service = services[draft.service] ?? 'Custom service'
  return draft.model ? `${service}: ${draft.model}` : service
}

// A key is needed for a service on the internet, unless one is saved already.
export function needsKey(draft: Draft, editing: Connection | null) {
  return draft.way === 'service' && !editing?.key_hint
}
