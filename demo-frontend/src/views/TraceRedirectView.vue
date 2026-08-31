<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpRight, GitBranch, LoaderCircle } from 'lucide-vue-next'

import { useSystemStore } from '@/stores/system'

const { t, locale } = useI18n()
const system = useSystemStore()

async function openTrace() {
  if (!system.capabilities) await system.load()
  const url = new URL(system.capabilities?.trace_url ?? 'http://127.0.0.1:3000')
  url.searchParams.set('lang', locale.value)
  url.searchParams.set('returnUrl', `${window.location.origin}/?lang=${locale.value}`)
  window.location.assign(url.toString())
}
onMounted(openTrace)
</script>

<template>
  <section class="placeholder-panel"><span class="chat-empty-icon"><GitBranch /></span><LoaderCircle class="spin" /><h1>{{ t('diagnostics.opening') }}</h1><p>{{ t('diagnostics.openingDescription') }}</p><button class="primary-button" type="button" @click="openTrace">{{ t('diagnostics.open') }}<ArrowUpRight :size="15" /></button></section>
</template>
