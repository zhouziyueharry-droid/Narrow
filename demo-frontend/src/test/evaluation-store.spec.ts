import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useEvaluationStore } from '@/stores/evaluations'
import type { EvaluationResult, Job } from '@/types'

class FakeEventSource {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSED = 2

  readonly url: string
  readyState = FakeEventSource.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string | URL) {
    this.url = String(url)
  }

  addEventListener() {}

  close() {
    this.readyState = FakeEventSource.CLOSED
  }
}

function job(status: Job['status']): Job {
  return {
    id: 'native_01',
    mode: 'native',
    status,
    code: `job.${status}`,
    created_at: '2026-08-30T00:00:00Z',
    config: {
      count: 2,
      provider: 'local',
      model: 'deepseek-v4-flash',
      realistic_verbalizer: 'template',
      seed: 42,
    },
    progress: { completed: status === 'completed' ? 2 : 1, total: 2 },
  }
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('evaluation live recovery', () => {
  it('loads a completed result through the five-second polling fallback', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('EventSource', FakeEventSource)
    const completedResult: EvaluationResult = { mode: 'native', metrics: { hit_rate_at_10: 1 }, sessions: [] }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/evaluations' && init?.method === 'POST') return Response.json(job('running'))
      if (url.endsWith('/result')) return Response.json(completedResult)
      if (url.endsWith('/native_01')) return Response.json(job('completed'))
      return Response.json({ error: { code: 'unknown' } }, { status: 404 })
    }))

    setActivePinia(createPinia())
    const store = useEvaluationStore()
    await store.start({
      mode: 'native', count: 2, provider: 'local', model: 'deepseek-v4-flash', realistic_verbalizer: 'template',
    })

    expect(store.activeJob?.status).toBe('running')
    await vi.advanceTimersByTimeAsync(5_000)

    expect(store.activeJob?.status).toBe('completed')
    expect(store.result).toEqual(completedResult)
    expect(store.connectionState).toBe('completed')
    expect(store.lastSyncedAt).toBeTruthy()
    store.closeEvents()
  })

  it('loads completed sessions while the evaluation is still running', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('EventSource', FakeEventSource)
    const partialResult: EvaluationResult = {
      mode: 'native',
      metrics: { hit_rate_at_10: 1, mrr: 0.5 },
      sessions: [{
        id: 'public_0001', sample_id: 'public_0001', scenario: 'buying', hit: true, success: true,
        first_hit_turn: 2, best_rank: 2, turn_count: 2, errors: [], conversation: [],
      }],
      partial: true,
      completed_sessions: 1,
      total_sessions: 2,
    }
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/evaluations' && init?.method === 'POST') return Response.json(job('running'))
      if (url.endsWith('/live-result')) return Response.json({ result: partialResult })
      if (url.endsWith('/native_01')) return Response.json(job('running'))
      return Response.json({ error: { code: 'unknown' } }, { status: 404 })
    }))

    setActivePinia(createPinia())
    const store = useEvaluationStore()
    await store.start({
      mode: 'native', count: 2, provider: 'local', model: 'deepseek-v4-flash', realistic_verbalizer: 'template',
    })

    await vi.advanceTimersByTimeAsync(5_000)

    expect(store.activeJob?.status).toBe('running')
    expect(store.result).toEqual(partialResult)
    expect(store.result?.sessions[0]?.id).toBe('public_0001')
    expect(store.connectionState).toBe('polling')
    store.closeEvents()
  })
})
