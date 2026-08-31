<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from 'reka-ui'
import { ArrowRight, CheckCircle2, Clock3, History, LoaderCircle, Trash2, XCircle } from 'lucide-vue-next'

import { ApiError } from '@/api'
import { useSystemStore } from '@/stores/system'
import type { Job } from '@/types'

const { t, d } = useI18n()
const router = useRouter()
const system = useSystemStore()
const selectedIds = ref<Set<string>>(new Set())
const pendingDeleteIds = ref<string[]>([])
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const activeStatuses = new Set(['queued', 'running', 'finalizing_diagnostics'])
const deletableRuns = computed(() => system.runs.filter(isDeletable))
const allSelected = computed(() => deletableRuns.value.length > 0 && deletableRuns.value.every((run) => selectedIds.value.has(run.id)))
const someSelected = computed(() => selectedIds.value.size > 0 && !allSelected.value)

onMounted(() => system.refreshRuns())

function isDeletable(run: Job) {
  return !run.protected && !activeStatuses.has(run.status)
}

function openRun(run: Job) {
  const routeName = run.mode === 'native' ? 'native' : run.mode === 'simulator-techjam' ? 'simulator-techjam' : 'simulator-realistic'
  router.push({ name: routeName, query: { runId: run.id } })
}

function toggleRun(runId: string, event: Event) {
  const next = new Set(selectedIds.value)
  if ((event.target as HTMLInputElement).checked) next.add(runId)
  else next.delete(runId)
  selectedIds.value = next
}

function toggleAll(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  selectedIds.value = checked ? new Set(deletableRuns.value.map((run) => run.id)) : new Set()
}

function requestDelete(ids: string[]) {
  pendingDeleteIds.value = ids
  deleteError.value = null
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!pendingDeleteIds.value.length || deleting.value) return
  deleting.value = true
  deleteError.value = null
  try {
    const result = await system.deleteRuns(pendingDeleteIds.value)
    const deleted = new Set(result.deleted)
    selectedIds.value = new Set([...selectedIds.value].filter((id) => !deleted.has(id)))
    pendingDeleteIds.value = []
    deleteOpen.value = false
  } catch (reason: unknown) {
    deleteError.value = reason instanceof ApiError ? reason.code : 'unknown'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <section class="page-heading">
    <div><p class="eyebrow"><History :size="13" /> {{ t('runs.eyebrow') }}</p><h1>{{ t('runs.title') }}</h1><p>{{ t('runs.description') }}</p></div>
  </section>

  <div v-if="system.runs.length" class="runs-toolbar">
    <span>{{ t('runs.selectedCount', { count: selectedIds.size }) }}</span>
    <button class="runs-delete-selected" type="button" :disabled="!selectedIds.size" @click="requestDelete([...selectedIds])"><Trash2 :size="14" />{{ t('runs.deleteSelected') }}</button>
  </div>

  <section class="runs-table-card">
    <div class="runs-table-head">
      <label class="run-selector" :title="t('runs.selectAll')"><input type="checkbox" :checked="allSelected" :indeterminate="someSelected" :aria-label="t('runs.selectAll')" @change="toggleAll" /></label>
      <div class="runs-table-columns"><span>{{ t('runs.run') }}</span><span>{{ t('runs.mode') }}</span><span>{{ t('runs.samples') }}</span><span>{{ t('runs.status') }}</span><span>{{ t('runs.created') }}</span><span /></div>
      <span>{{ t('runs.actions') }}</span>
    </div>

    <div v-for="run in system.runs" :key="run.id" class="run-row" :class="{ selected: selectedIds.has(run.id) }">
      <label class="run-selector" :title="isDeletable(run) ? t('runs.selectRun', { id: run.id }) : t('runs.activeProtected')">
        <input type="checkbox" :checked="selectedIds.has(run.id)" :disabled="!isDeletable(run)" :aria-label="t('runs.selectRun', { id: run.id })" @change="toggleRun(run.id, $event)" />
      </label>
      <button class="run-open-button" type="button" @click="openRun(run)">
        <span><strong>{{ run.id }}</strong><small>{{ run.config.model }}</small></span>
        <span>{{ t(`evaluation.${run.mode === 'native' ? 'native' : run.mode === 'simulator-techjam' ? 'techjam' : 'realistic'}.title`) }}</span>
        <span>{{ run.config.count }}</span>
        <span class="run-status"><LoaderCircle v-if="activeStatuses.has(run.status)" class="spin" /><CheckCircle2 v-else-if="run.status === 'completed'" /><XCircle v-else />{{ t(`status.${run.code}`, run.code) }}</span>
        <span><Clock3 :size="13" />{{ d(new Date(run.created_at), 'short') }}</span>
        <ArrowRight :size="16" />
      </button>
      <button class="run-delete-button" type="button" :disabled="!isDeletable(run)" :title="isDeletable(run) ? t('runs.deleteRun') : t('runs.activeProtected')" :aria-label="`${t('runs.deleteRun')}: ${run.id}`" @click="requestDelete([run.id])"><Trash2 :size="14" /></button>
    </div>

    <div v-if="!system.runs.length" class="table-empty"><History /><h2>{{ t('runs.emptyTitle') }}</h2><p>{{ t('runs.emptyDescription') }}</p></div>
  </section>

  <DialogRoot v-model:open="deleteOpen">
    <DialogPortal>
      <DialogOverlay class="dialog-overlay" />
      <DialogContent class="dialog-content">
        <DialogTitle>{{ t('runs.deleteTitle') }}</DialogTitle>
        <DialogDescription>{{ t('runs.deleteDescription', { count: pendingDeleteIds.length }) }}</DialogDescription>
        <p v-if="deleteError" class="inline-error">{{ t(`errors.${deleteError}`, deleteError) }}</p>
        <div class="dialog-actions"><DialogClose class="secondary-button dark-text" :disabled="deleting">{{ t('runs.cancel') }}</DialogClose><button class="danger-button" type="button" :disabled="deleting" @click="confirmDelete"><LoaderCircle v-if="deleting" class="spin" :size="14" /><Trash2 v-else :size="14" />{{ deleting ? t('runs.deleting') : t('runs.confirmDelete') }}</button></div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
