import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { i18n, setLocale } from '@/i18n'
import type { ChatMessage, ChatSession } from '@/types'
import ChatView from '@/views/ChatView.vue'

const session: ChatSession = {
  id: 'chat_test_01',
  title: 'New shopping conversation',
  created_at: '2026-08-30T00:00:00Z',
  updated_at: '2026-08-30T00:00:00Z',
  settings_revision: 1,
  messages: [],
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('human chat sending', () => {
  it('focuses a suggested prompt and immediately shows send progress', async () => {
    setLocale('zh-CN')
    let resolveAgent!: (response: Response) => void
    const pendingAgent = new Promise<Response>((resolve) => { resolveAgent = resolve })
    let completed = false
    const userMessage: ChatMessage = { role: 'user', content: '想找适合城市旅行的轻便防水鞋', created_at: '2026-08-30T00:00:01Z' }
    const assistantMessage: ChatMessage = { role: 'assistant', content: '可以先确认鞋码和预算。', created_at: '2026-08-30T00:00:02Z', recommendations: [] }

    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/capabilities') return Response.json({ catalog: { available: true, product_count: 1, bytes: 1 }, public_set: { available: true, session_count: 1 }, deepseek_configured: true, trace_url: 'http://127.0.0.1:3000', limits: { native: 200, 'simulator-techjam': 200, 'simulator-realistic': 100 } })
      if (url === '/api/settings') return Response.json({ provider: 'deepseek', model: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com', realistic_verbalizer: 'template', revision: 1, deepseek_configured: true, model_presets: ['deepseek-v4-flash'] })
      if (url === '/api/evaluations') return Response.json({ runs: [] })
      if (url === '/api/chat/sessions' && init?.method === 'POST') return Response.json(session, { status: 201 })
      if (url === '/api/chat/sessions' && !init?.method) return Response.json({ sessions: completed ? [{ ...session, message_count: 2 }] : [] })
      if (url === `/api/chat/sessions/${session.id}/messages`) return pendingAgent
      if (url === `/api/chat/sessions/${session.id}`) return Response.json({ ...session, messages: [userMessage, assistantMessage] })
      return Response.json({ error: { code: 'unknown' } }, { status: 404 })
    }))

    const wrapper = mount(ChatView, { attachTo: document.body, global: { plugins: [createPinia(), i18n] } })
    await flushPromises()
    const suggestion = wrapper.get('.suggestion-list button')
    const textarea = wrapper.get<HTMLTextAreaElement>('.composer-wrap textarea')
    await suggestion.trigger('click')

    expect(textarea.element.value).toBe(userMessage.content)
    expect(document.activeElement).toBe(textarea.element)

    await wrapper.get('.composer-wrap > button').trigger('click')
    await wrapper.vm.$nextTick()
    expect(textarea.element.value).toBe('')
    expect(wrapper.text()).toContain(userMessage.content)
    expect(wrapper.text()).toContain('正在理解偏好并排序商品')
    expect(wrapper.get('.composer-wrap > button').attributes('disabled')).toBeDefined()

    completed = true
    resolveAgent(Response.json(assistantMessage))
    await flushPromises()
    expect(wrapper.text()).toContain(assistantMessage.content)
    expect(wrapper.find('.assistant-thinking').exists()).toBe(false)
    wrapper.unmount()
  })
})
