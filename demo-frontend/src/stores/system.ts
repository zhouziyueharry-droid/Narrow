import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { apiRequest } from '@/api'
import type { Capabilities, Job, RunDeleteResult, Settings } from '@/types'

export const useSystemStore = defineStore('system', () => {
  const capabilities = ref<Capabilities | null>(null)
  const settings = ref<Settings | null>(null)
  const runs = ref<Job[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ready = computed(() => Boolean(capabilities.value?.catalog.available && capabilities.value?.public_set.available))
  const latestRun = computed(() => runs.value[0] ?? null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const [caps, currentSettings, history] = await Promise.all([
        apiRequest<Capabilities>('/api/capabilities'),
        apiRequest<Settings>('/api/settings'),
        apiRequest<{ runs: Job[] }>('/api/evaluations'),
      ])
      capabilities.value = caps
      settings.value = currentSettings
      runs.value = history.runs
    } catch (reason: any) {
      error.value = reason.code ?? 'api.unavailable'
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(next: Omit<Settings, 'revision' | 'deepseek_configured' | 'model_presets'>) {
    settings.value = await apiRequest<Settings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(next),
    })
    return settings.value
  }

  async function refreshRuns() {
    runs.value = (await apiRequest<{ runs: Job[] }>('/api/evaluations')).runs
  }

  async function deleteRuns(ids: string[]) {
    const result = await apiRequest<RunDeleteResult>('/api/evaluations', {
      method: 'DELETE',
      body: JSON.stringify({ ids }),
    })
    const deleted = new Set(result.deleted)
    runs.value = runs.value.filter((run) => !deleted.has(run.id))
    return result
  }

  return { capabilities, settings, runs, loading, error, ready, latestRun, load, saveSettings, refreshRuns, deleteRuns }
})
