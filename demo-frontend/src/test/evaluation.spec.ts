import { describe, expect, it } from 'vitest'

import { diagnosticUrl } from '@/api'
import { evaluationLimit, evaluationRunQuery, isValidSessionCount } from '@/evaluation'
import { CUSTOM_MODEL_VALUE, mergeModelPresets } from '@/model-options'

describe('evaluation contracts', () => {
  it('enforces the three session limits', () => {
    expect(evaluationLimit('native')).toBe(200)
    expect(evaluationLimit('simulator-techjam')).toBe(200)
    expect(evaluationLimit('simulator-realistic')).toBe(100)
    expect(isValidSessionCount('native', 1)).toBe(true)
    expect(isValidSessionCount('native', 200)).toBe(true)
    expect(isValidSessionCount('native', 201)).toBe(false)
    expect(isValidSessionCount('simulator-realistic', 100)).toBe(true)
    expect(isValidSessionCount('simulator-realistic', 101)).toBe(false)
  })

  it('builds an auditable bilingual trace deep link', () => {
    const url = new URL(diagnosticUrl('http://127.0.0.1:3000', 'run_01', 'public_0001', 3, 'zh-CN', 'target'))
    expect(Object.fromEntries(url.searchParams)).toMatchObject({
      runId: 'run_01', session: 'public_0001', turn: '3', diagnosticMode: 'target', lang: 'zh-CN',
    })
    expect(url.searchParams.get('returnUrl')).toContain(window.location.origin)
  })

  it('persists the active run and language without dropping existing query state', () => {
    expect(evaluationRunQuery({ filter: 'miss' }, 'native_01', 'zh-CN')).toEqual({
      filter: 'miss', runId: 'native_01', lang: 'zh-CN',
    })
  })

  it('always exposes both DeepSeek V4 presets and keeps custom models available', () => {
    expect(mergeModelPresets()).toEqual(['deepseek-v4-flash', 'deepseek-v4-pro'])
    expect(mergeModelPresets(['deepseek-v4-flash', 'team-custom-model'])).toEqual([
      'deepseek-v4-flash',
      'deepseek-v4-pro',
      'team-custom-model',
    ])
    expect(CUSTOM_MODEL_VALUE).toBe('__custom__')
  })
})
