<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import {
  ArrowRight,
  Bot,
  ChartNoAxesCombined,
  Check,
  FlaskConical,
  GitBranch,
  History,
  MessageSquareText,
  PackageSearch,
  Server,
  Settings2,
  Sparkles,
} from 'lucide-vue-next'

import { useSystemStore } from '@/stores/system'

const { t, d, n } = useI18n()
const system = useSystemStore()

const features = computed(() => [
  { to: '/chat', icon: MessageSquareText, tone: 'cyan', title: t('home.cards.chat.title'), description: t('home.cards.chat.description'), meta: t('home.cards.chat.meta') },
  { to: '/evaluations/native', icon: ChartNoAxesCombined, tone: 'coral', title: t('home.cards.native.title'), description: t('home.cards.native.description'), meta: t('home.cards.native.meta') },
  { to: '/evaluations/simulator-techjam', icon: Bot, tone: 'lime', title: t('home.cards.techjam.title'), description: t('home.cards.techjam.description'), meta: t('home.cards.techjam.meta') },
  { to: '/evaluations/simulator-realistic', icon: FlaskConical, tone: 'violet', title: t('home.cards.realistic.title'), description: t('home.cards.realistic.description'), meta: t('home.cards.realistic.meta') },
  { to: '/trace', icon: GitBranch, tone: 'navy', title: t('home.cards.trace.title'), description: t('home.cards.trace.description'), meta: t('home.cards.trace.meta') },
  { to: '/settings', icon: Settings2, tone: 'sand', title: t('home.cards.settings.title'), description: t('home.cards.settings.description'), meta: t('home.cards.settings.meta') },
  { to: '/runs', icon: History, tone: 'cyan', title: t('home.cards.runs.title'), description: t('home.cards.runs.description'), meta: t('home.cards.runs.meta') },
])

const latestRoute = computed(() => {
  const run = system.latestRun
  if (!run) return '/runs'
  const page = run.mode === 'native' ? '/evaluations/native' : run.mode === 'simulator-techjam' ? '/evaluations/simulator-techjam' : '/evaluations/simulator-realistic'
  return `${page}?runId=${encodeURIComponent(run.id)}`
})

onMounted(() => { if (!system.capabilities) system.load() })
</script>

<template>
  <section class="hero-grid">
    <div class="hero-copy">
      <p class="eyebrow"><Sparkles :size="14" /> {{ t('home.labEyebrow') }}</p>
      <h1>Shopping Copilot Demo</h1>
      <h2>Tiktok TechJam 2026</h2>
      <p class="hero-description">{{ t('home.heroDescription') }}</p>
      <div class="hero-actions">
        <RouterLink class="primary-button" to="/chat">{{ t('home.startChat') }}<ArrowRight :size="17" /></RouterLink>
        <RouterLink class="secondary-button" to="/evaluations/native">{{ t('home.runEvaluation') }}</RouterLink>
      </div>
      <div class="hero-proof">
        <span><Check :size="14" /> {{ t('home.proof.local') }}</span>
        <span><Check :size="14" /> {{ t('home.proof.bilingual') }}</span>
        <span><Check :size="14" /> {{ t('home.proof.traceable') }}</span>
      </div>
    </div>

    <div class="shopping-visual">
      <picture>
        <source media="(min-width: 641px) and (max-width: 980px)" srcset="/hero-shopping-wide-v2.png" />
        <img src="/hero-shopping-v2.png" :alt="t('home.heroVisualAlt')" />
      </picture>
    </div>
  </section>

  <section class="status-ribbon" :aria-label="t('common.systemStatus')">
    <div><span class="status-icon"><Server /></span><span><small>{{ t('common.apiReady') }}</small><strong>{{ system.error ? t('errors.api.unavailable') : system.capabilities ? t('common.ready') : t('common.checking') }}</strong></span></div>
    <div><span class="status-icon"><PackageSearch /></span><span><small>{{ t('home.status.catalog') }}</small><strong>{{ system.capabilities ? n(system.capabilities.catalog.product_count) : '—' }}</strong></span></div>
    <div><span class="status-icon"><ChartNoAxesCombined /></span><span><small>{{ t('home.status.publicSet') }}</small><strong>{{ system.capabilities?.public_set.session_count ?? '—' }}</strong></span></div>
    <div><span class="status-icon"><Bot /></span><span><small>DeepSeek</small><strong>{{ system.capabilities ? (system.capabilities.deepseek_configured ? t('settings.configured') : t('settings.notConfigured')) : t('common.checking') }}</strong></span></div>
    <div><span class="status-icon"><GitBranch /></span><span><small>Trace</small><strong>{{ system.capabilities?.trace_url ? t('common.ready') : t('common.checking') }}</strong></span></div>
  </section>

  <section class="recent-run-card">
    <div><p class="eyebrow">{{ t('home.recent.eyebrow') }}</p><h2>{{ t('home.recent.title') }}</h2></div>
    <template v-if="system.latestRun">
      <span><small>{{ system.latestRun.mode }}</small><strong>{{ system.latestRun.config.count }} {{ t('runs.samples') }}</strong></span>
      <span><small>{{ t('runs.status') }}</small><strong>{{ t(`status.${system.latestRun.code}`, system.latestRun.code) }}</strong></span>
      <span><small>{{ t('runs.created') }}</small><strong>{{ d(new Date(system.latestRun.created_at), 'short') }}</strong></span>
      <RouterLink :to="latestRoute">{{ t('home.recent.open') }}<ArrowRight :size="15" /></RouterLink>
    </template>
    <p v-else>{{ t('home.recent.empty') }}</p>
  </section>

  <section class="feature-section">
    <div class="section-heading">
      <div><p class="eyebrow">{{ t('home.featureEyebrow') }}</p><h2>{{ t('home.featureTitle') }}</h2></div>
      <RouterLink to="/runs">{{ t('home.viewRuns') }} <ArrowRight :size="15" /></RouterLink>
    </div>
    <div class="feature-grid">
      <RouterLink v-for="feature in features" :key="feature.to" :to="feature.to" class="feature-card">
        <span class="feature-icon" :class="`tone-${feature.tone}`"><component :is="feature.icon" /></span>
        <span class="feature-copy"><small>{{ feature.meta }}</small><strong>{{ feature.title }}</strong><p>{{ feature.description }}</p></span>
        <ArrowRight class="feature-arrow" :size="18" />
      </RouterLink>
    </div>
  </section>
</template>
