<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import {
  Bot,
  ChartNoAxesCombined,
  ChevronRight,
  FlaskConical,
  GitBranch,
  Languages,
  Menu,
  MessageSquareText,
  Settings2,
  ShoppingBag,
  Sparkles,
  X,
} from 'lucide-vue-next'

import { setLocale, type SupportedLocale } from './i18n'
import { useSystemStore } from './stores/system'

const { locale, t } = useI18n()
const route = useRoute()
const mobileOpen = ref(false)
const system = useSystemStore()

const navigation = computed(() => [
  { to: '/', label: t('navigation.home'), icon: ShoppingBag },
  { to: '/chat', label: t('navigation.chat'), icon: MessageSquareText },
  { to: '/evaluations/native', label: t('navigation.native'), icon: ChartNoAxesCombined },
  { to: '/evaluations/simulator-techjam', label: t('navigation.techjam'), icon: Bot },
  { to: '/evaluations/simulator-realistic', label: t('navigation.realistic'), icon: FlaskConical },
  { to: '/runs', label: t('navigation.runs'), icon: Sparkles },
  { to: '/trace', label: t('navigation.trace'), icon: GitBranch },
  { to: '/settings', label: t('navigation.settings'), icon: Settings2 },
])

function toggleLocale() {
  setLocale((locale.value === 'zh-CN' ? 'en' : 'zh-CN') as SupportedLocale)
}

onMounted(() => {
  const requested = new URLSearchParams(window.location.search).get('lang')
  if (requested === 'zh-CN' || requested === 'en') setLocale(requested)
  system.load()
})
</script>

<template>
  <div class="app-frame">
    <aside class="sidebar" :class="{ 'sidebar-open': mobileOpen }">
      <div class="brand-lockup">
        <span class="brand-mark"><ShoppingBag :size="22" /></span>
        <span>
          <strong>Shopping Copilot Demo</strong>
          <small>TIKTOK TECHJAM 2026</small>
        </span>
        <button class="icon-button sidebar-close" :aria-label="t('common.close')" @click="mobileOpen = false"><X /></button>
      </div>

      <nav class="main-nav" :aria-label="t('navigation.primary')">
        <RouterLink
          v-for="item in navigation"
          :key="item.to"
          :to="route.path === item.to ? { path: item.to, query: route.query } : item.to"
          :class="{ active: route.path === item.to }"
          @click="mobileOpen = false"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
          <ChevronRight class="nav-chevron" :size="15" />
        </RouterLink>
      </nav>

      <div class="sidebar-note">
        <span class="status-dot" />
        <div><strong>{{ t('common.localDemo') }}</strong><small>{{ t('common.localOnly') }}</small></div>
      </div>
    </aside>

    <div class="app-main">
      <header class="topbar">
        <button class="icon-button menu-button" :aria-label="t('common.menu')" @click="mobileOpen = true"><Menu /></button>
        <div class="topbar-title">
          <span>{{ t('common.workspace') }}</span>
          <strong>{{ route.meta.titleKey ? t(String(route.meta.titleKey)) : t('navigation.home') }}</strong>
        </div>
        <div class="topbar-actions">
          <span class="api-status"><span class="status-dot" :class="{ offline: system.error }" />{{ system.error ? t('errors.api.unavailable') : t('common.apiReady') }}</span>
          <button class="locale-button" type="button" @click="toggleLocale">
            <Languages :size="17" />
            <span>{{ locale === 'zh-CN' ? '中文' : 'EN' }}</span>
          </button>
        </div>
      </header>

      <main class="page-container">
        <RouterView />
      </main>
    </div>
  </div>
</template>
