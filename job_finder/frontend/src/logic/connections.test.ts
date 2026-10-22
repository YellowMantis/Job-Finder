import { describe, expect, it } from 'vitest'
import type { Connection } from '../api/types'
import { draftOf, emptyDraft, fieldsOf, needsKey, suggestedName, type Draft } from './connections'

const services = { groq: 'Groq', openai: 'OpenAI' }
const saved = (changes: Partial<Connection>): Connection => ({
  id: 'c1', name: 'x', kind: 'claude', service: '', base_url: '', model: '', key_hint: '',
  ...changes,
})

describe('the add-a-connection form', () => {
  it('turns each way into what the back end expects', () => {
    expect(fieldsOf({ ...emptyDraft, way: 'claude' }, 'Claude Code'))
      .toEqual({ name: 'Claude Code', kind: 'claude' })
    expect(fieldsOf({ ...emptyDraft, way: 'service', service: 'groq', model: 'big' }, 'G'))
      .toEqual({ name: 'G', kind: 'api', service: 'groq', model: 'big' })
    // A model on this PC: Ollama has its own kind, LM Studio speaks the OpenAI format.
    expect(fieldsOf({ ...emptyDraft, way: 'local', local: { runner: 'ollama', model: 'llama' } }, 'L'))
      .toEqual({ name: 'L', kind: 'ollama', model: 'llama' })
    expect(fieldsOf({ ...emptyDraft, way: 'local', local: { runner: 'lmstudio', model: 'qwen' } }, 'L'))
      .toEqual({ name: 'L', kind: 'api', service: 'lmstudio', model: 'qwen' })
  })

  it('makes the Claude API its own kind of connection', () => {
    const draft: Draft = { ...emptyDraft, way: 'service', service: 'anthropic', model: 'claude-x' }
    expect(fieldsOf(draft, 'Claude API')).toEqual({ name: 'Claude API', kind: 'anthropic', model: 'claude-x' })
    expect(draftOf(saved({ kind: 'anthropic', service: 'anthropic', model: 'claude-x' })))
      .toMatchObject({ way: 'service', service: 'anthropic', model: 'claude-x' })
  })

  it('sends an address only for a custom service', () => {
    const draft: Draft = { ...emptyDraft, way: 'service', service: 'custom',
      baseUrl: 'https://ai.example.com/v1', model: 'm' }
    expect(fieldsOf(draft, 'Mine').base_url).toBe('https://ai.example.com/v1')
    expect(fieldsOf({ ...draft, service: 'groq' }, 'G').base_url).toBeUndefined()
  })

  it('reads a saved connection back into the form', () => {
    expect(draftOf(saved({ kind: 'ollama', model: 'llama' })).local)
      .toEqual({ runner: 'ollama', model: 'llama' })
    expect(draftOf(saved({ kind: 'api', service: 'lmstudio', model: 'qwen' })).way).toBe('local')
    expect(draftOf(saved({ kind: 'api', service: 'groq', model: 'big' })))
      .toMatchObject({ way: 'service', service: 'groq', model: 'big' })
  })

  it('suggests a name from the choices', () => {
    expect(suggestedName({ ...emptyDraft, way: 'service', service: 'groq', model: 'big' }, services))
      .toBe('Groq: big')
    expect(suggestedName({ ...emptyDraft, way: 'local', local: { runner: 'ollama', model: 'llama' } },
      services)).toBe('Ollama: llama')
  })

  it('asks for a key only for an internet service without one saved', () => {
    const draft = { ...emptyDraft, way: 'service' as const }
    expect(needsKey(draft, null)).toBe(true)
    expect(needsKey(draft, saved({ key_hint: 'gsk_…3f9a' }))).toBe(false)
    expect(needsKey({ ...emptyDraft, way: 'local' }, null)).toBe(false)
  })
})
