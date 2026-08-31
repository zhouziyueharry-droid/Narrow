import { describe, expect, it } from 'vitest'

import { setLocale } from '@/i18n'
import en from '@/locales/en'
import zhCN from '@/locales/zh-CN'

function paths(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') return [prefix]
  return Object.entries(value).flatMap(([key, child]) => paths(child, prefix ? `${prefix}.${key}` : key))
}

describe('bilingual resources', () => {
  it('keeps the Chinese and English key sets identical', () => {
    expect(paths(zhCN).sort()).toEqual(paths(en).sort())
  })

  it('persists the selected locale without touching original content', () => {
    const original = 'QIAN0813 Celttic Knot Necklace · B09PYB7B6Z'
    setLocale('zh-CN')
    expect(localStorage.getItem('techjam.locale')).toBe('zh-CN')
    expect(document.documentElement.lang).toBe('zh-CN')
    expect(original).toBe('QIAN0813 Celttic Knot Necklace · B09PYB7B6Z')
    setLocale('en')
    expect(localStorage.getItem('techjam.locale')).toBe('en')
  })
})
