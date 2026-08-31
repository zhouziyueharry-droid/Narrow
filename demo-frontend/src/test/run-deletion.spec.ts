import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n, setLocale } from '@/i18n'
import type { Job } from '@/types'
import RunsView from '@/views/RunsView.vue'

function run(id: string, status: Job['status']): Job {
  return {
    id,
    mode: 'native',
    status,
    code: `job.${status}`,
    created_at: '2026-08-30T00:00:00Z',
    config: { count: 2, provider: 'local', model: 'local', realistic_verbalizer: 'template', seed: 42 },
    progress: { completed: status === 'completed' ? 2 : 1, total: 2 },
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

describe('run history deletion', () => {
  it('supports selection and confirmation while protecting active runs', async () => {
    setLocale('en')
    const completed = run('native_completed_01', 'completed')
    const running = run('native_running_01', 'running')
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'DELETE') {
        return Response.json({ deleted: [completed.id], not_found: [] })
      }
      return Response.json({ runs: [completed, running] })
    })
    vi.stubGlobal('fetch', fetchMock)
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/runs', component: RunsView },
        { path: '/evaluations/native', name: 'native', component: { template: '<div />' } },
        { path: '/evaluations/simulator-techjam', name: 'simulator-techjam', component: { template: '<div />' } },
        { path: '/evaluations/simulator-realistic', name: 'simulator-realistic', component: { template: '<div />' } },
      ],
    })
    await router.push('/runs')
    await router.isReady()
    const wrapper = mount(RunsView, { attachTo: document.body, global: { plugins: [createPinia(), i18n, router] } })
    await flushPromises()

    const rowCheckboxes = wrapper.findAll<HTMLInputElement>('.run-row input[type="checkbox"]')
    expect(rowCheckboxes).toHaveLength(2)
    expect(rowCheckboxes[1].element.disabled).toBe(true)
    await rowCheckboxes[0].setValue(true)
    expect(wrapper.text()).toContain('1 selected')

    await wrapper.get('.runs-delete-selected').trigger('click')
    await flushPromises()
    const dialog = document.querySelector('.dialog-content') as HTMLElement
    expect(dialog.textContent).toContain('including results, logs, and diagnostics')
    const confirm = [...dialog.querySelectorAll('button')].find((button) => button.textContent?.includes('Delete permanently'))
    expect(confirm).toBeTruthy()
    confirm?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()

    const deleteCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'DELETE')
    expect(deleteCall?.[0]).toBe('/api/evaluations')
    expect(JSON.parse(String(deleteCall?.[1]?.body))).toEqual({ ids: [completed.id] })
    expect(wrapper.findAll('.run-row')).toHaveLength(1)
    expect(wrapper.text()).toContain(running.id)
    wrapper.unmount()
  })
})
