import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import { i18n, setLocale } from '@/i18n'

describe('unified demo home', () => {
  it('renders the fixed title, subtitle, and every capability entry in English', async () => {
    setLocale('en')
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const data = url.endsWith('/api/capabilities')
        ? { catalog: { available: true, product_count: 50000, bytes: 1 }, public_set: { available: true, session_count: 200 }, deepseek_configured: false, trace_url: 'http://127.0.0.1:3000', limits: { native: 200, 'simulator-techjam': 200, 'simulator-realistic': 100 } }
        : url.endsWith('/api/settings')
          ? { provider: 'local', model: 'deepseek-v4-flash', base_url: 'https://api.deepseek.com', realistic_verbalizer: 'template', revision: 1, deepseek_configured: false, model_presets: [] }
          : { runs: [] }
      return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }))
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: HomeView }, { path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
    await router.push('/')
    await router.isReady()
    const wrapper = mount(HomeView, { global: { plugins: [createPinia(), i18n, router] } })
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('Shopping Copilot Demo')
    expect(wrapper.get('.hero-copy h2').text()).toBe('Tiktok TechJam 2026')
    expect(wrapper.get('.shopping-visual img').attributes('src')).toBe('/hero-shopping-v2.png')
    for (const label of ['Human Shopping Copilot', 'Native Evaluator', 'User Simulator · TechJam', 'User Simulator · Realistic', 'Trace Visualizer', 'DeepSeek & Models', 'Run History']) {
      expect(wrapper.text()).toContain(label)
    }
    expect(wrapper.findAll('.feature-card')).toHaveLength(7)
  })
})
