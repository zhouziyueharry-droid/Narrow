<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import {
  Activity,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Filter,
  GitBranch,
  LoaderCircle,
  MessageSquareText,
  Play,
  RotateCcw,
  Search,
  Square,
  Target,
  XCircle,
} from 'lucide-vue-next'

import { diagnosticUrl } from '@/api'
import { evaluationLimit, evaluationRunQuery } from '@/evaluation'
import { useEvaluationStore } from '@/stores/evaluations'
import { useSystemStore } from '@/stores/system'
import type { EvaluationMode, EvaluationSession, Provider } from '@/types'

const { t, locale, n, d } = useI18n()
const route = useRoute()
const router = useRouter()
const system = useSystemStore()
const evaluations = useEvaluationStore()
const mode = computed(() => route.meta.mode as EvaluationMode)
const maximum = computed(() => evaluationLimit(mode.value))
const count = ref(10)
const provider = ref<Provider>('local')
const verbalizer = ref<'template' | 'deepseek'>('template')
const query = ref('')
const resultFilter = ref<'all' | 'hit' | 'miss'>('all')
const scenarioFilter = ref('all')
const errorsOnly = ref(false)
const selected = ref<EvaluationSession | null>(null)

const modeKey = computed(() => mode.value === 'native' ? 'native' : mode.value === 'simulator-techjam' ? 'techjam' : 'realistic')
const running = computed(() => evaluations.activeJob && ['queued', 'running', 'finalizing_diagnostics'].includes(evaluations.activeJob.status))
const progress = computed(() => {
  const job = evaluations.activeJob
  if (!job?.progress.total) return 0
  return Math.round((job.progress.completed / job.progress.total) * 100)
})
const jobErrorCount = computed(() => evaluations.result?.metrics?.model_usage?.agent?.error_count ?? evaluations.activeJob?.metrics?.model_usage?.agent?.error_count ?? (evaluations.activeJob?.error ? 1 : 0))
const sessions = computed(() => evaluations.result?.sessions ?? [])
const liveCompleted = computed(() => evaluations.result?.completed_sessions ?? sessions.value.length)
const liveTotal = computed(() => evaluations.result?.total_sessions ?? evaluations.activeJob?.progress.total ?? sessions.value.length)
const diagnosticsReady = computed(() => evaluations.activeJob?.status === 'completed' && !evaluations.result?.partial)
const scenarios = computed(() => Array.from(new Set(sessions.value.flatMap(item => [item.scenario, item.persona].filter(Boolean) as string[]))).sort())
const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return sessions.value.filter(session => {
    const hitMatch = resultFilter.value === 'all' || (resultFilter.value === 'hit' ? session.hit : !session.hit)
    const scenarioMatch = scenarioFilter.value === 'all' || session.scenario === scenarioFilter.value || session.persona === scenarioFilter.value
    const errorMatch = !errorsOnly.value || (session.errors?.length ?? 0) > 0
    const text = [session.id, session.target_parent_asin, session.target?.title, session.persona].filter(Boolean).join(' ').toLowerCase()
    return hitMatch && scenarioMatch && errorMatch && (!needle || text.includes(needle))
  })
})
const metricCards = computed(() => {
  const metrics = evaluations.result?.metrics ?? {}
  const evaluation = metrics.evaluation ?? metrics
  if (mode.value === 'simulator-realistic') return [
    { label: t('metrics.successRate'), value: evaluation.success_rate, format: 'percent' },
    { label: 'MRR', value: evaluation.mrr, format: 'number' },
    { label: t('metrics.meanTurns'), value: metrics.turn_metrics?.mean_executed_turns, format: 'number' },
    { label: t('metrics.hardSatisfaction'), value: metrics.mode_specific_metrics?.hard_constraint_satisfaction_at_acceptance, format: 'percent' },
    { label: t('metrics.tokens'), value: metrics.model_usage?.combined?.reported_token_usage?.total_tokens, format: 'number' },
    { label: t('metrics.latency'), value: metrics.latency?.agent?.p95_ms, format: 'latency' },
  ]
  return [
    { label: 'Hit Rate@10', value: evaluation.hit_rate_at_10, format: 'percent' },
    { label: 'MRR', value: evaluation.mrr, format: 'number' },
    { label: 'MTTC', value: evaluation.mttc, format: 'number' },
    { label: t('metrics.technicalScore'), value: evaluation.recommended_technical_score, format: 'number' },
    { label: t('metrics.tokens'), value: metrics.reported_token_usage?.total_tokens ?? metrics.model_usage?.combined?.reported_token_usage?.total_tokens, format: 'number' },
    { label: t('metrics.latency'), value: metrics.latency?.agent?.p95_ms ?? (metrics.elapsed_seconds != null ? metrics.elapsed_seconds * 1000 : null), format: 'latency' },
  ]
})

function currentRouteRunId() {
  return typeof route.query.runId === 'string' ? route.query.runId : null
}

async function resyncCurrentRun() {
  const runId = currentRouteRunId() ?? evaluations.activeJob?.id
  if (runId) await evaluations.resync(runId)
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') void resyncCurrentRun()
}

function handleResume() {
  void resyncCurrentRun()
}

onMounted(async () => {
  if (!system.settings) await system.load()
  provider.value = system.settings?.provider ?? 'local'
  let runId = currentRouteRunId()
  if (!runId) {
    const recoverable = system.runs.find(run => run.mode === mode.value && ['queued', 'running', 'finalizing_diagnostics'].includes(run.status))
    if (recoverable) {
      runId = recoverable.id
      await evaluations.loadJob(runId)
      await router.replace({ query: evaluationRunQuery(route.query, runId, locale.value) })
    }
  }
  if (runId && runId !== evaluations.activeJob?.id) await evaluations.loadJob(runId)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  window.addEventListener('focus', handleResume)
  window.addEventListener('online', handleResume)
  window.addEventListener('pageshow', handleResume)
})
onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  window.removeEventListener('focus', handleResume)
  window.removeEventListener('online', handleResume)
  window.removeEventListener('pageshow', handleResume)
  evaluations.closeEvents()
})
watch(mode, () => { evaluations.result = null; selected.value = null; count.value = 10 })
watch(() => route.query.runId, runId => {
  if (typeof runId === 'string' && runId !== evaluations.activeJob?.id) void evaluations.loadJob(runId)
  else if (!runId && evaluations.activeJob?.mode === mode.value) {
    void router.replace({ query: evaluationRunQuery(route.query, evaluations.activeJob.id, locale.value) })
  }
})
watch(filtered, list => { if (selected.value && !list.some(item => item.id === selected.value?.id)) selected.value = list[0] ?? null; else if (!selected.value) selected.value = list[0] ?? null })

async function start() {
  const job = await evaluations.start({
    mode: mode.value,
    count: count.value,
    provider: provider.value,
    model: system.settings?.model ?? 'deepseek-v4-flash',
    realistic_verbalizer: mode.value === 'simulator-realistic' ? verbalizer.value : 'template',
  })
  await router.replace({ query: evaluationRunQuery(route.query, job.id, locale.value) })
}

function resetFilters() {
  query.value = ''; resultFilter.value = 'all'; scenarioFilter.value = 'all'; errorsOnly.value = false
}

function scenarioLabel(value: string) {
  const known = ['buying', 'browsing', 'boundary', 'intent_override', 'realistic']
  return known.includes(value) ? t(`evaluation.scenarios.${value}`) : value
}

function openDiagnostics(session: EvaluationSession, turn?: number) {
  if (!diagnosticsReady.value || !evaluations.activeJob || !system.capabilities) return
  window.open(diagnosticUrl(
    system.capabilities.trace_url,
    evaluations.activeJob.id,
    session.id,
    turn,
    locale.value,
    mode.value === 'simulator-realistic' ? 'agent' : 'target',
  ), '_blank', 'noopener')
}

function formatMetric(value: any, format: string) {
  if (value == null) return '—'
  if (typeof value === 'number' && format === 'percent') return new Intl.NumberFormat(locale.value, { style: 'percent', maximumFractionDigits: 1 }).format(value)
  if (typeof value === 'number' && format === 'latency') return `${n(value, { maximumFractionDigits: 1 })} ms`
  if (typeof value === 'number') return n(value, { maximumFractionDigits: 4 })
  return String(value)
}
</script>

<template>
  <section class="page-heading">
    <div><p class="eyebrow"><Activity :size="13" /> {{ t(`evaluation.${modeKey}.eyebrow`) }}</p><h1>{{ t(`evaluation.${modeKey}.title`) }}</h1><p>{{ t(`evaluation.${modeKey}.description`) }}</p></div>
    <span class="protocol-badge">{{ t(`evaluation.protocols.${modeKey}`) }}</span>
  </section>

  <section class="run-config-card">
    <div class="config-field wide"><label for="session-count">{{ t('evaluation.sessionCount') }}</label><div class="range-control"><input id="session-count" v-model.number="count" type="range" min="1" :max="maximum" :disabled="Boolean(running)" /><input v-model.number="count" type="number" min="1" :max="maximum" :disabled="Boolean(running)" /></div><small>{{ t('evaluation.limit', { max: maximum }) }}</small></div>
    <div class="config-field"><label for="provider">{{ t('settings.provider') }}</label><select id="provider" v-model="provider" :disabled="Boolean(running)"><option value="local">{{ t('settings.localFallback') }}</option><option value="deepseek" :disabled="!system.settings?.deepseek_configured">DeepSeek</option></select></div>
    <div v-if="mode === 'simulator-realistic'" class="config-field"><label for="verbalizer">{{ t('settings.verbalizer') }}</label><select id="verbalizer" v-model="verbalizer" :disabled="Boolean(running)"><option value="template">Template</option><option value="deepseek" :disabled="!system.settings?.deepseek_configured">DeepSeek</option></select></div>
    <div class="run-actions"><button v-if="!running" class="primary-button" type="button" @click="start"><Play :size="16" />{{ t('evaluation.start') }}</button><button v-else class="danger-button" type="button" @click="evaluations.cancel"><Square :size="14" />{{ t('evaluation.stop') }}</button></div>
  </section>

  <section v-if="evaluations.activeJob" class="job-strip" :class="evaluations.activeJob.status">
    <div class="job-status-icon"><LoaderCircle v-if="running" class="spin" /><CheckCircle2 v-else-if="evaluations.activeJob.status === 'completed'" /><CircleAlert v-else /></div>
    <div><small>{{ evaluations.activeJob.id }} · {{ evaluations.activeJob.config.provider === 'local' ? t('settings.localFallback') : evaluations.activeJob.config.model }} · {{ t('evaluation.errors') }} {{ jobErrorCount }}</small><strong>{{ t(`status.${evaluations.activeJob.code}`, evaluations.activeJob.code) }}</strong><small class="sync-state" :class="evaluations.connectionState">{{ t(`evaluation.connection.${evaluations.connectionState}`) }}<template v-if="evaluations.lastSyncedAt"> · {{ t('evaluation.lastSynced') }} {{ d(new Date(evaluations.lastSyncedAt), 'short') }}</template></small></div>
    <div class="progress-track"><span :style="{ width: `${progress}%` }" /></div>
    <strong>{{ evaluations.activeJob.progress.completed }} / {{ evaluations.activeJob.progress.total }}</strong>
  </section>

  <p v-if="evaluations.activeJob?.error" class="inline-error">{{ t(`errors.${evaluations.activeJob.error.code}`, evaluations.activeJob.error.code) }}<small>{{ evaluations.activeJob.error.detail }}</small></p>
  <p v-if="evaluations.error" class="inline-error">{{ t(`errors.${evaluations.error}`, evaluations.error) }}</p>

  <div v-if="evaluations.result?.partial" class="live-result-note" aria-live="polite">
    <span><LoaderCircle class="spin" :size="16" />{{ t('evaluation.liveBadge') }}</span>
    <p>{{ t('evaluation.liveResult', { completed: liveCompleted, total: liveTotal }) }}</p>
  </div>

  <section v-if="evaluations.result" class="metric-grid">
    <article v-for="metric in metricCards" :key="metric.label"><small>{{ metric.label }}</small><strong>{{ formatMetric(metric.value, metric.format) }}</strong></article>
  </section>

  <section v-if="evaluations.result" class="session-browser">
    <aside class="session-list-panel">
      <div class="session-panel-header"><div><p class="eyebrow">{{ t('evaluation.sessionExplorer') }}</p><h2>{{ t('evaluation.sessions') }}</h2></div><span>{{ filtered.length }}</span></div>
      <div class="session-filters">
        <label class="search-input"><Search :size="15" /><input v-model="query" :placeholder="t('evaluation.searchPlaceholder')" /></label>
        <div class="filter-grid"><select v-model="resultFilter"><option value="all">{{ t('common.all') }}</option><option value="hit">{{ t('evaluation.hit') }}</option><option value="miss">{{ t('evaluation.miss') }}</option></select><select v-model="scenarioFilter"><option value="all">{{ t('evaluation.allScenarios') }}</option><option v-for="scenario in scenarios" :key="scenario" :value="scenario">{{ scenarioLabel(scenario) }}</option></select></div>
        <label class="check-filter"><input v-model="errorsOnly" type="checkbox" />{{ t('evaluation.errorsOnly') }}</label>
        <button class="reset-filter" type="button" @click="resetFilters"><RotateCcw :size="13" />{{ t('common.clear') }}</button>
      </div>
      <div class="evaluation-session-list">
        <button v-for="session in filtered" :key="session.id" type="button" :class="{ selected: selected?.id === session.id }" @click="selected = session">
          <span :class="['result-marker', session.hit ? 'hit' : 'miss']"><CheckCircle2 v-if="session.hit" /><XCircle v-else /></span>
          <span><small>{{ session.id }}</small><strong>{{ session.target?.title || session.goal?.category || session.persona || session.target_parent_asin }}</strong><em>{{ scenarioLabel(session.scenario) }} · {{ session.turn_count }} {{ t('evaluation.turns') }}</em></span>
        </button>
        <p v-if="!filtered.length" class="small-empty">{{ t('evaluation.noMatches') }}</p>
      </div>
    </aside>

    <section v-if="selected" class="session-detail-panel">
      <header class="session-detail-header"><div><span :class="['result-badge', selected.hit ? 'hit' : 'miss']">{{ selected.hit ? t('evaluation.hit') : t('evaluation.miss') }}</span><small>{{ selected.id }} · {{ scenarioLabel(selected.scenario) }}</small><h2>{{ selected.target?.title || selected.target_parent_asin || selected.persona }}</h2><p>{{ selected.target_parent_asin || selected.goal?.goal_type }}</p></div><button class="secondary-button dark-text" type="button" :disabled="!diagnosticsReady" :title="diagnosticsReady ? t('diagnostics.open') : t('diagnostics.afterCompletion')" @click="openDiagnostics(selected, selected.first_hit_turn || selected.turn_count)"><GitBranch :size="16" />{{ mode === 'simulator-realistic' ? t('diagnostics.viewAgentTrace') : t('diagnostics.open') }}<ArrowUpRight :size="14" /></button></header>
      <div class="session-facts"><span><small>{{ t('evaluation.firstHit') }}</small><strong>{{ selected.first_hit_turn ?? '—' }}</strong></span><span><small>{{ t('evaluation.bestRank') }}</small><strong>{{ selected.best_rank ?? '—' }}</strong></span><span><small>{{ t('evaluation.errors') }}</small><strong>{{ selected.errors?.length ?? 0 }}</strong></span></div>
      <div class="transcript-heading"><MessageSquareText :size="16" /><strong>{{ t('evaluation.fullConversation') }}</strong><span>{{ t('chat.originalContent') }}</span></div>
      <div class="transcript-list">
        <article v-for="turn in selected.conversation" :key="turn.turn" class="turn-card">
          <div class="turn-index"><span>{{ turn.turn }}</span><small>{{ t('evaluation.turn') }}</small></div>
          <div class="turn-dialogue"><p><strong>{{ t('chat.you') }}</strong>{{ turn.user }}</p><p><strong>Agent</strong>{{ turn.assistant }}</p><div class="turn-meta"><span v-if="turn.ask_attribute">ask · {{ turn.ask_attribute }}</span><span><Clock3 :size="11" />{{ n((turn.latency_ms ?? 0) / 1000, { maximumFractionDigits: 2 }) }}s</span><span>{{ t('evaluation.recommendationCount', { count: turn.recommendations.length }) }}</span><span v-if="turn.target_rank"><Target :size="11" />#{{ turn.target_rank }}</span></div><details v-if="turn.recommendations.length" class="turn-recommendations"><summary>{{ t('evaluation.recommendations') }}</summary><div><code v-for="(asin, rank) in turn.recommendations.slice(0, 10)" :key="asin">#{{ rank + 1 }} · {{ asin }}</code></div></details></div>
          <button class="trace-turn-button" type="button" :disabled="!diagnosticsReady" :title="diagnosticsReady ? t('diagnostics.open') : t('diagnostics.afterCompletion')" @click="openDiagnostics(selected, turn.turn)"><GitBranch :size="15" /></button>
        </article>
      </div>
    </section>
  </section>

  <section v-else-if="!evaluations.activeJob" class="evaluation-empty"><span><Bot /></span><h2>{{ t('evaluation.emptyTitle') }}</h2><p>{{ t('evaluation.emptyDescription') }}</p></section>
</template>
