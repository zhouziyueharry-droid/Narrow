import { defineStore } from 'pinia'
import { ref } from 'vue'

import { ApiError, apiRequest } from '@/api'
import type { ChatMessage, ChatSession } from '@/types'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const active = ref<ChatSession | null>(null)
  const sending = ref(false)
  const error = ref<string | null>(null)

  async function loadSessions() {
    const data = await apiRequest<{ sessions: Array<Omit<ChatSession, 'messages'> & { message_count: number }> }>('/api/chat/sessions')
    sessions.value = data.sessions.map(session => ({ ...session, messages: [] }))
    if (active.value && !sessions.value.some(session => session.id === active.value?.id)) active.value = null
    if (!active.value && sessions.value[0]) await select(sessions.value[0].id)
  }

  async function create() {
    const session = await apiRequest<ChatSession>('/api/chat/sessions', { method: 'POST' })
    sessions.value.unshift(session)
    active.value = session
    return session
  }

  async function select(id: string) {
    active.value = await apiRequest<ChatSession>(`/api/chat/sessions/${id}`)
  }

  async function remove(id: string) {
    await apiRequest<void>(`/api/chat/sessions/${id}`, { method: 'DELETE' })
    sessions.value = sessions.value.filter(item => item.id !== id)
    if (active.value?.id === id) active.value = null
    if (!active.value && sessions.value[0]) await select(sessions.value[0].id)
  }

  async function send(content: string): Promise<boolean> {
    if (sending.value) return false
    sending.value = true
    error.value = null
    let target: ChatSession | null = null
    let optimistic: ChatMessage | null = null
    try {
      if (!active.value) await create()
      if (!active.value) throw new Error('chat.session_not_found')
      target = active.value
      const sessionId = target.id
      optimistic = { role: 'user', content, created_at: new Date().toISOString() }
      target.messages.push(optimistic)
      const response = await apiRequest<ChatMessage>(`/api/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ message: content, top_k: 10 }),
      })
      target.messages.push(response)
      await loadSessions()
      if (active.value?.id === sessionId) await select(sessionId)
      return true
    } catch (reason: unknown) {
      if (target && optimistic) target.messages = target.messages.filter(item => item !== optimistic)
      error.value = reason instanceof ApiError ? reason.code : 'chat.agent_failed'
      throw reason
    } finally {
      sending.value = false
    }
  }

  return { sessions, active, sending, error, loadSessions, create, select, remove, send }
})
