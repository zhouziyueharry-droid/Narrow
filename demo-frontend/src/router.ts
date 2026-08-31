import { createRouter, createWebHistory } from 'vue-router'

import HomeView from './views/HomeView.vue'
import ChatView from './views/ChatView.vue'
import EvaluationView from './views/EvaluationView.vue'
import RunsView from './views/RunsView.vue'
import SettingsView from './views/SettingsView.vue'
import TraceRedirectView from './views/TraceRedirectView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/chat', name: 'chat', component: ChatView, meta: { titleKey: 'navigation.chat' } },
    { path: '/evaluations/native', name: 'native', component: EvaluationView, meta: { titleKey: 'navigation.native', mode: 'native' } },
    { path: '/evaluations/simulator-techjam', name: 'simulator-techjam', component: EvaluationView, meta: { titleKey: 'navigation.techjam', mode: 'simulator-techjam' } },
    { path: '/evaluations/simulator-realistic', name: 'simulator-realistic', component: EvaluationView, meta: { titleKey: 'navigation.realistic', mode: 'simulator-realistic' } },
    { path: '/runs', name: 'runs', component: RunsView, meta: { titleKey: 'navigation.runs' } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { titleKey: 'navigation.settings' } },
    { path: '/trace', name: 'trace', component: TraceRedirectView, meta: { titleKey: 'navigation.trace' } },
  ],
})
