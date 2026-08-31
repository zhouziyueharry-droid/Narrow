import { createI18n } from 'vue-i18n'

import en from './locales/en'
import zhCN from './locales/zh-CN'

export type SupportedLocale = 'zh-CN' | 'en'

const stored = localStorage.getItem('techjam.locale')
const initialLocale: SupportedLocale = stored === 'zh-CN' || stored === 'en'
  ? stored
  : navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: { 'zh-CN': zhCN, en },
  datetimeFormats: {
    'zh-CN': { short: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' } },
    en: { short: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } },
  },
  missingWarn: import.meta.env.DEV,
  fallbackWarn: import.meta.env.DEV,
})

document.documentElement.lang = initialLocale

export function setLocale(locale: SupportedLocale) {
  i18n.global.locale.value = locale
  localStorage.setItem('techjam.locale', locale)
  document.documentElement.lang = locale
}
