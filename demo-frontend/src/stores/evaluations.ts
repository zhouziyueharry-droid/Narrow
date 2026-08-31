import { defineStore } from 'pinia'
import { ref } from 'vue'

import { apiRequest } from '@/api'
import type { EvaluationMode, EvaluationResult, Job, Provider } from '@/types'

export type EvaluationConnectionState = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'polling' | 'completed'

const POLL_INTERVAL_MS = 5_000
const RECONNECT_DELAY_MS = 1_500
const ACTIVE_STATUSES = new Set(['queued', 'running', 'finalizing_diagnostics'])
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'interrupted'])

export const useEvaluationStore = defineStore('evaluations', () => {
  const activeJob = ref<Job | null>(null)
  const result = ref<EvaluationResult | null>(null)
  const error = ref<string | null>(null)
  const connectionState = ref<EvaluationConnectionState>('idle')
  const lastSyncedAt = ref<string | null>(null)
  let eventSource: EventSource | null = null
  let pollTimer: number | null = null
  let reconnectTimer: number | null = null
  let watchedJobId: string | null = null
  let syncInFlight: Promise<void> | null = null
  let liveResultInFlight: Promise<void> | null = null

  async function start(options: {
    mode: EvaluationMode
    count: number
    provider: Provider
    model: string
    realistic_verbalizer: 'template' | 'deepseek'
  }) {
    closeEvents()
    result.value = null
    error.value = null
    try {
      activeJob.value = await apiRequest<Job>('/api/evaluations', {
        method: 'POST',
        body: JSON.stringify(options),
      })
      beginWatching(activeJob.value.id)
      return activeJob.value
    } catch (reason: any) {
      error.value = reason.code ?? 'unknown'
      throw reason
    }
  }

  async function loadJob(jobId: string) {
    closeEvents()
    activeJob.value = await apiRequest<Job>(`/api/evaluations/${jobId}`)
    lastSyncedAt.value = new Date().toISOString()
    error.value = null
    if (activeJob.value.status === 'completed') {
      await loadResult(jobId)
      connectionState.value = 'completed'
    } else if (ACTIVE_STATUSES.has(activeJob.value.status)) {
      await loadLiveResult(jobId)
      beginWatching(jobId)
    } else {
      connectionState.value = 'idle'
    }
  }

  async function loadResult(jobId: string) {
    const completedResult = await apiRequest<EvaluationResult>(`/api/evaluations/${jobId}/result`)
    if (activeJob.value?.id === jobId) result.value = completedResult
  }

  async function loadLiveResult(jobId: string) {
    if (liveResultInFlight) return liveResultInFlight
    liveResultInFlight = (async () => {
      try {
        const response = await apiRequest<{ result: EvaluationResult | null }>(`/api/evaluations/${jobId}/live-result`)
        if (activeJob.value?.id === jobId && response.result) result.value = response.result
      } finally {
        liveResultInFlight = null
      }
    })()
    return liveResultInFlight
  }

  function beginWatching(jobId: string) {
    closeEvents()
    watchedJobId = jobId
    connectionState.value = 'connecting'
    pollTimer = window.setInterval(() => { void syncWatchedJob(jobId) }, POLL_INTERVAL_MS)
    connectEvents(jobId)
  }

  function connectEvents(jobId: string) {
    if (watchedJobId !== jobId || !ACTIVE_STATUSES.has(activeJob.value?.status ?? '')) return
    eventSource?.close()
    eventSource = new EventSource(`/api/evaluations/${jobId}/events`)
    eventSource.onopen = () => {
      if (watchedJobId === jobId) connectionState.value = 'live'
    }
    const update: EventListener = async (event) => {
      if (watchedJobId !== jobId) return
      const payload = JSON.parse((event as MessageEvent<string>).data)
      lastSyncedAt.value = payload.timestamp ?? new Date().toISOString()
      error.value = null
      if (activeJob.value?.id === jobId) {
        activeJob.value.status = payload.status
        activeJob.value.code = payload.code
        activeJob.value.progress = payload.progress
      }
      const renderedSessions = result.value?.sessions.length ?? 0
      if (ACTIVE_STATUSES.has(payload.status) && payload.progress?.completed > renderedSessions) {
        await loadLiveResult(jobId)
      }
      if (TERMINAL_STATUSES.has(payload.status)) {
        eventSource?.close()
        eventSource = null
        await syncWatchedJob(jobId)
      }
    }
    eventSource.addEventListener('snapshot', update)
    eventSource.addEventListener('progress', update)
    eventSource.onerror = () => {
      if (watchedJobId !== jobId) return
      eventSource?.close()
      eventSource = null
      connectionState.value = 'reconnecting'
      void syncWatchedJob(jobId).finally(() => scheduleReconnect(jobId))
    }
  }

  function scheduleReconnect(jobId: string) {
    if (watchedJobId !== jobId || !ACTIVE_STATUSES.has(activeJob.value?.status ?? '') || reconnectTimer) return
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connectEvents(jobId)
    }, RECONNECT_DELAY_MS)
  }

  async function syncWatchedJob(jobId: string) {
    if (watchedJobId !== jobId) return
    if (syncInFlight) return syncInFlight
    syncInFlight = (async () => {
      try {
        const job = await apiRequest<Job>(`/api/evaluations/${jobId}`)
        if (watchedJobId !== jobId) return
        activeJob.value = job
        lastSyncedAt.value = new Date().toISOString()
        error.value = null
        if (job.status === 'completed') {
          await loadResult(jobId)
          finishWatching('completed')
        } else if (TERMINAL_STATUSES.has(job.status)) {
          finishWatching('idle')
        } else {
          await loadLiveResult(jobId)
          if (!eventSource || eventSource.readyState !== EventSource.OPEN) {
            connectionState.value = 'polling'
          }
        }
      } catch {
        if (watchedJobId === jobId) {
          error.value = 'api.unavailable'
          connectionState.value = 'reconnecting'
        }
      } finally {
        syncInFlight = null
      }
    })()
    return syncInFlight
  }

  async function resync(jobId?: string) {
    const target = jobId ?? watchedJobId ?? activeJob.value?.id
    if (!target) return
    if (watchedJobId === target) await syncWatchedJob(target)
    else await loadJob(target)
  }

  async function cancel() {
    if (!activeJob.value) return
    activeJob.value = await apiRequest<Job>(`/api/evaluations/${activeJob.value.id}/cancel`, { method: 'POST' })
    closeEvents()
  }

  function stopTransports() {
    eventSource?.close()
    eventSource = null
    if (pollTimer) window.clearInterval(pollTimer)
    pollTimer = null
    if (reconnectTimer) window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  function finishWatching(state: EvaluationConnectionState) {
    stopTransports()
    watchedJobId = null
    connectionState.value = state
  }

  function closeEvents() {
    stopTransports()
    watchedJobId = null
    syncInFlight = null
    if (connectionState.value !== 'completed') connectionState.value = 'idle'
  }

  return { activeJob, result, error, connectionState, lastSyncedAt, start, loadJob, loadResult, loadLiveResult, resync, cancel, closeEvents }
})
