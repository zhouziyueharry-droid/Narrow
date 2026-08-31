<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, KeyRound, Languages, LoaderCircle, LockKeyhole, Save, Server, Settings2, TestTube2 } from 'lucide-vue-next'

import { apiRequest } from '@/api'
import { setLocale, type SupportedLocale } from '@/i18n'
import { CUSTOM_MODEL_VALUE, mergeModelPresets } from '@/model-options'
import { useSystemStore } from '@/stores/system'

const { t, locale } = useI18n()
const system = useSystemStore()
const saving = ref(false)
const testing = ref(false)
const saved = ref(false)
const testResult = ref<Record<string, any> | null>(null)
const error = ref<string | null>(null)
const form = reactive({ provider: 'local' as 'local' | 'deepseek', model: '', base_url: '', realistic_verbalizer: 'template' as 'template' | 'deepseek', reranker: 'precise' as 'precise' | 'lambdamart' })
const modelChoice = ref('deepseek-v4-flash')
const customModel = ref('')
const modelOptions = computed(() => mergeModelPresets(system.settings?.model_presets))

function hydrate() {
  if (!system.settings) return
  form.provider = system.settings.provider
  form.reranker = system.settings.reranker ?? 'precise'
  form.model = system.settings.model
  if (modelOptions.value.includes(system.settings.model)) {
    modelChoice.value = system.settings.model
    customModel.value = ''
  } else {
    modelChoice.value = CUSTOM_MODEL_VALUE
    customModel.value = system.settings.model
  }
  form.base_url = system.settings.base_url
  form.realistic_verbalizer = system.settings.realistic_verbalizer
}
onMounted(async () => { if (!system.settings) await system.load(); hydrate() })
watch(() => system.settings, hydrate)

function updateModelChoice() {
  form.model = modelChoice.value === CUSTOM_MODEL_VALUE ? customModel.value : modelChoice.value
}

function updateCustomModel() {
  if (modelChoice.value === CUSTOM_MODEL_VALUE) form.model = customModel.value
}

async function save() {
  saving.value = true; saved.value = false; error.value = null
  try {
    await system.saveSettings(form)
    saved.value = true
    window.setTimeout(() => { saved.value = false }, 2500)
  } catch (reason: any) { error.value = reason.code ?? 'unknown' }
  finally { saving.value = false }
}

async function testConnection() {
  testing.value = true; testResult.value = null; error.value = null
  try { testResult.value = await apiRequest('/api/settings/deepseek/test', { method: 'POST' }) }
  catch (reason: any) { error.value = reason.code ?? 'deepseek.connection_failed' }
  finally { testing.value = false }
}
</script>

<template>
  <section class="page-heading"><div><p class="eyebrow"><Settings2 :size="13" /> {{ t('settings.eyebrow') }}</p><h1>{{ t('settings.title') }}</h1><p>{{ t('settings.description') }}</p></div></section>
  <div class="settings-grid">
    <section class="settings-card">
      <header><span><Server /></span><div><h2>{{ t('settings.runtimeTitle') }}</h2><p>{{ t('settings.runtimeDescription') }}</p></div></header>
      <div class="settings-form">
        <label><span>{{ t('settings.provider') }}</span><select v-model="form.provider"><option value="local">{{ t('settings.localFallback') }}</option><option value="deepseek" :disabled="!system.settings?.deepseek_configured">DeepSeek</option></select></label>
        <label><span>{{ t('settings.model') }}</span><select v-model="modelChoice" data-testid="model-select" @change="updateModelChoice"><option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option><option :value="CUSTOM_MODEL_VALUE">{{ t('settings.customModel') }}</option></select><input v-if="modelChoice === CUSTOM_MODEL_VALUE" v-model="customModel" data-testid="custom-model-input" :placeholder="t('settings.customModelPlaceholder')" @input="updateCustomModel" /><small>{{ t('settings.modelHint') }}</small></label>
        <label><span>{{ t('settings.reranker') }}</span><select v-model="form.reranker"><option value="precise">Precise (final default)</option><option value="lambdamart">LambdaMART (frozen 2000)</option></select><small>{{ t('settings.rerankerHint') }}</small></label>
        <label><span>{{ t('settings.baseUrl') }}</span><input v-model="form.base_url" type="url" readonly /><small>{{ t('settings.baseUrlHint') }}</small></label>
        <label><span>{{ t('settings.verbalizer') }}</span><select v-model="form.realistic_verbalizer"><option value="template">Template</option><option value="deepseek" :disabled="!system.settings?.deepseek_configured">DeepSeek</option></select><small>{{ t('settings.verbalizerHint') }}</small></label>
      </div>
      <div class="settings-actions"><button class="primary-button" type="button" :disabled="saving" @click="save"><LoaderCircle v-if="saving" class="spin" /><Save v-else :size="16" />{{ t('common.save') }}</button><span v-if="saved" class="saved-message"><CheckCircle2 />{{ t('settings.saved') }}</span></div>
    </section>

    <section class="settings-card security-card">
      <header><span><LockKeyhole /></span><div><h2>{{ t('settings.securityTitle') }}</h2><p>{{ t('settings.securityDescription') }}</p></div></header>
      <div class="key-status" :class="{ configured: system.settings?.deepseek_configured }"><KeyRound /><span><small>DEEPSEEK_API_KEY</small><strong>{{ system.settings?.deepseek_configured ? t('settings.configured') : t('settings.notConfigured') }}</strong></span></div>
      <p class="security-copy">{{ t('settings.keyNotice') }}</p>
      <button class="secondary-button dark-text" type="button" :disabled="testing || !system.settings?.deepseek_configured" @click="testConnection"><LoaderCircle v-if="testing" class="spin" /><TestTube2 v-else :size="16" />{{ t('settings.testConnection') }}</button>
      <div v-if="testResult" class="connection-result"><CheckCircle2 /><span><strong>{{ t('settings.connectionOk') }}</strong><small>{{ testResult.model }} · {{ testResult.latency_ms }}ms</small></span></div>
    </section>

    <section class="settings-card language-card">
      <header><span><Languages /></span><div><h2>{{ t('settings.languageTitle') }}</h2><p>{{ t('settings.languageDescription') }}</p></div></header>
      <div class="language-options"><button type="button" :class="{ selected: locale === 'zh-CN' }" @click="setLocale('zh-CN' as SupportedLocale)"><strong>中文</strong><small>简体中文</small></button><button type="button" :class="{ selected: locale === 'en' }" @click="setLocale('en' as SupportedLocale)"><strong>English</strong><small>EN</small></button></div>
    </section>
  </div>
  <p v-if="error" class="inline-error">{{ t(`errors.${error}`, error) }}</p>
</template>
