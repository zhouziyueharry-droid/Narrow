<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { DialogClose, DialogContent, DialogDescription, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import {
  Bot,
  ChevronDown,
  ChevronRight,
  CirclePlus,
  Clock3,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  PackageSearch,
  Send,
  ShoppingBag,
  Sparkles,
  Star,
  Trash2,
} from 'lucide-vue-next'

import { DEFAULT_INLINE_RECOMMENDATIONS, hiddenRecommendationCount, inlineRecommendationLimit } from '@/chat-recommendations'
import { useChatStore } from '@/stores/chat'
import { useSystemStore } from '@/stores/system'

const { t, locale, n } = useI18n()
const chat = useChatStore()
const system = useSystemStore()
const draft = ref('')
const composer = ref<HTMLTextAreaElement | null>(null)
const stream = ref<HTMLElement | null>(null)
const lastFailed = ref('')
const deleteOpen = ref(false)
const pendingDelete = ref<string | null>(null)
const expandedRecommendations = ref<Set<string>>(new Set())

const suggestions = computed(() => [
  t('chat.suggestions.shoes'),
  t('chat.suggestions.bag'),
  t('chat.suggestions.gift'),
])
const latestAssistant = computed(() => [...(chat.active?.messages ?? [])].reverse().find(item => item.role === 'assistant'))

function formatPrice(price?: number | null) {
  return price == null ? '—' : new Intl.NumberFormat(locale.value, { style: 'currency', currency: 'USD' }).format(price)
}

onMounted(async () => {
  if (!system.capabilities) await system.load()
  await chat.loadSessions()
  if (!chat.active) await chat.create()
})

watch(() => chat.active?.messages.length, async () => {
  await nextTick()
  stream.value?.scrollTo?.({ top: stream.value.scrollHeight, behavior: 'smooth' })
})

async function send() {
  const message = draft.value.trim()
  if (!message || chat.sending) return
  lastFailed.value = ''
  const request = chat.send(message)
  if (chat.sending) draft.value = ''
  await request.catch(() => {
    lastFailed.value = message
    if (!draft.value) draft.value = message
  })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

async function chooseSuggestion(value: string) {
  draft.value = value
  await nextTick()
  composer.value?.focus()
  composer.value?.setSelectionRange(value.length, value.length)
}

function recommendationMessageKey(createdAt: string, index: number) {
  return `${createdAt}-${index}`
}

function recommendationsExpanded(key: string) {
  return expandedRecommendations.value.has(key)
}

function toggleRecommendations(key: string) {
  const next = new Set(expandedRecommendations.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expandedRecommendations.value = next
}

async function retry() {
  if (!lastFailed.value || chat.sending) return
  const message = lastFailed.value
  lastFailed.value = ''
  await chat.send(message).catch(() => { lastFailed.value = message })
}

function requestDelete(id: string) {
  pendingDelete.value = id
  deleteOpen.value = true
}

async function confirmDelete() {
  if (!pendingDelete.value) return
  await chat.remove(pendingDelete.value)
  pendingDelete.value = null
  deleteOpen.value = false
}
</script>

<template>
  <section class="page-heading compact-heading">
    <div><p class="eyebrow"><Sparkles :size="13" /> {{ t('chat.eyebrow') }}</p><h1>{{ t('chat.title') }}</h1><p>{{ t('chat.description') }}</p></div>
    <span class="model-pill"><span class="status-dot" />{{ system.settings?.provider === 'deepseek' ? system.settings.model : t('settings.localFallback') }}</span>
  </section>

  <section class="chat-workspace">
    <aside class="conversation-sidebar">
      <button class="new-chat-button" type="button" @click="chat.create"><CirclePlus :size="17" />{{ t('chat.newConversation') }}</button>
      <p class="panel-label">{{ t('chat.conversations') }}</p>
      <div class="conversation-list">
        <div
          v-for="session in chat.sessions"
          :key="session.id"
          class="conversation-item"
          :class="{ selected: session.id === chat.active?.id }"
        >
          <button class="conversation-select" type="button" @click="chat.select(session.id)"><MessageSquareText :size="15" /><span><strong>{{ session.title }}</strong><small>{{ session.message_count ?? session.messages.length }} {{ t('chat.messages') }}</small></span></button>
          <button class="delete-chat" type="button" :aria-label="t('chat.delete')" @click.stop="requestDelete(session.id)"><Trash2 :size="14" /></button>
        </div>
      </div>
      <div class="privacy-note"><Lightbulb :size="16" /><p>{{ t('chat.localNotice') }}</p></div>
    </aside>

    <section class="chat-panel">
      <div ref="stream" class="message-stream">
        <div v-if="!chat.active?.messages.length" class="chat-empty">
          <span class="chat-empty-icon"><ShoppingBag /></span>
          <p class="eyebrow">SHOPPING COPILOT</p>
          <h2>{{ t('chat.emptyTitle') }}</h2>
          <p>{{ t('chat.emptyDescription') }}</p>
          <div class="suggestion-list">
            <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="chooseSuggestion(suggestion)">{{ suggestion }}<ChevronRight :size="15" /></button>
          </div>
        </div>

        <article v-for="(message, index) in chat.active?.messages" :key="`${message.created_at}-${index}`" class="message-row" :class="message.role">
          <span class="message-avatar"><Bot v-if="message.role === 'assistant'" :size="17" /><span v-else>{{ t('chat.you') }}</span></span>
          <div class="message-content">
            <div class="message-meta"><strong>{{ message.role === 'assistant' ? 'Shopping Copilot' : t('chat.you') }}</strong><span>{{ t('chat.originalContent') }}</span></div>
            <p>{{ message.content }}</p>
            <div v-if="message.ask_attribute" class="ask-chip">{{ t('chat.asking') }} · {{ message.ask_attribute }}</div>
            <div v-if="message.recommendations?.length" class="recommendation-block">
              <div class="inline-products">
                <article
                  v-for="product in message.recommendations.slice(0, inlineRecommendationLimit(recommendationsExpanded(recommendationMessageKey(message.created_at, index))))"
                  :key="product.parent_asin"
                  class="product-card"
                >
                  <div class="product-thumb"><PackageSearch /><span>{{ product.categories.at(-1)?.slice(0, 2) || 'AI' }}</span></div>
                  <div class="product-info"><small>{{ product.parent_asin }}</small><h3 :title="product.title">{{ product.title }}</h3><p>{{ product.brand || t('chat.brandUnknown') }}</p><p class="product-category">{{ product.categories.at(-1) || '—' }}</p><div><strong>{{ formatPrice(product.price) }}</strong><span><Star :size="12" />{{ product.rating ?? '—' }}</span></div><div v-if="product.score != null" class="product-score"><small>{{ t('chat.matchScore') }}</small><strong>{{ n(product.score, { maximumFractionDigits: 3 }) }}</strong></div></div>
                </article>
              </div>
              <button
                v-if="message.recommendations.length > DEFAULT_INLINE_RECOMMENDATIONS"
                class="product-expander"
                type="button"
                :aria-expanded="recommendationsExpanded(recommendationMessageKey(message.created_at, index))"
                @click="toggleRecommendations(recommendationMessageKey(message.created_at, index))"
              >
                <ChevronDown :class="{ expanded: recommendationsExpanded(recommendationMessageKey(message.created_at, index)) }" :size="15" />
                {{ recommendationsExpanded(recommendationMessageKey(message.created_at, index))
                  ? t('chat.showFewerProducts')
                  : t('chat.showMoreProducts', { count: hiddenRecommendationCount(message.recommendations.length) }) }}
              </button>
            </div>
            <div v-if="message.role === 'assistant'" class="message-stats"><span><Clock3 :size="12" />{{ n((message.latency_ms ?? 0) / 1000, { maximumFractionDigits: 2 }) }}s</span><span>{{ (message.usage?.prompt_tokens ?? 0) + (message.usage?.completion_tokens ?? 0) }} tokens</span></div>
          </div>
        </article>

        <div v-if="chat.sending" class="assistant-thinking"><span class="message-avatar"><Bot :size="17" /></span><LoaderCircle class="spin" /><span>{{ t('chat.thinking') }}</span></div>
        <p v-if="chat.error" class="inline-error">{{ t(`errors.${chat.error}`, chat.error) }}<button v-if="lastFailed" type="button" @click="retry">{{ t('chat.retry') }}</button></p>
      </div>

      <div class="composer-wrap">
        <textarea ref="composer" v-model="draft" :placeholder="t('chat.placeholder')" rows="1" :aria-label="t('chat.placeholder')" @keydown="onKeydown" />
        <button type="button" :disabled="!draft.trim() || chat.sending" :aria-label="t('chat.send')" @click="send"><Send :size="18" /></button>
        <small>{{ t('chat.composerHint') }}</small>
      </div>
    </section>

    <aside class="insight-panel">
      <div class="insight-heading"><PackageSearch :size="17" /><strong>{{ t('chat.recommendations') }}</strong><span>{{ latestAssistant?.recommendations?.length ?? 0 }}</span></div>
      <div v-if="latestAssistant?.recommendations?.length" class="insight-products">
        <article v-for="(product, index) in latestAssistant.recommendations.slice(0, 10)" :key="product.parent_asin"><span>{{ index + 1 }}</span><div><strong :title="product.title">{{ product.title }}</strong><small>{{ product.parent_asin }}</small><p>{{ product.brand || t('chat.brandUnknown') }} · {{ formatPrice(product.price) }} · ★ {{ product.rating ?? '—' }}</p><p v-if="product.categories.at(-1)">{{ product.categories.at(-1) }}</p></div></article>
      </div>
      <p v-else class="small-empty">{{ t('chat.noRecommendations') }}</p>
      <div class="intent-box">
        <p class="panel-label">{{ t('chat.intentState') }}</p>
        <dl>
          <div><dt>semantic_query</dt><dd>{{ latestAssistant?.intent?.semantic_query || '—' }}</dd></div>
          <div><dt>{{ t('chat.category') }}</dt><dd>{{ latestAssistant?.intent?.category || '—' }}</dd></div>
          <div><dt>{{ t('chat.constraints') }}</dt><dd>{{ latestAssistant?.intent?.active_constraints?.length ?? 0 }}</dd></div>
        </dl>
      </div>
    </aside>
  </section>

  <DialogRoot v-model:open="deleteOpen">
    <DialogPortal>
      <DialogOverlay class="dialog-overlay" />
      <DialogContent class="dialog-content">
        <DialogTitle>{{ t('chat.deleteTitle') }}</DialogTitle>
        <DialogDescription>{{ t('chat.deleteDescription') }}</DialogDescription>
        <div class="dialog-actions"><DialogClose class="secondary-button dark-text">{{ t('chat.cancel') }}</DialogClose><button class="danger-button" type="button" @click="confirmDelete">{{ t('chat.confirmDelete') }}</button></div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
