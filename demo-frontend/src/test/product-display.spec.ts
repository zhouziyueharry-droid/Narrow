import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  DEFAULT_INLINE_RECOMMENDATIONS,
  hiddenRecommendationCount,
  inlineRecommendationLimit,
  MAX_INLINE_RECOMMENDATIONS,
} from '../chat-recommendations'

describe('shopping recommendation display', () => {
  it('shows four inline products by default and up to ten after expansion', () => {
    const view = readFileSync(resolve(process.cwd(), 'src/views/ChatView.vue'), 'utf8')
    const css = readFileSync(resolve(process.cwd(), 'src/styles.css'), 'utf8')

    expect(DEFAULT_INLINE_RECOMMENDATIONS).toBe(4)
    expect(MAX_INLINE_RECOMMENDATIONS).toBe(10)
    expect(inlineRecommendationLimit(false)).toBe(4)
    expect(inlineRecommendationLimit(true)).toBe(10)
    expect(hiddenRecommendationCount(10)).toBe(6)
    expect(hiddenRecommendationCount(3)).toBe(0)
    expect(view).toContain('message.recommendations.slice(0, inlineRecommendationLimit(')
    expect(view).toContain("t('chat.showMoreProducts'")
    expect(view).toContain('latestAssistant.recommendations.slice(0, 10)')
    expect(css).toContain('.product-info h3 { min-height: 26px;')
    expect(css).toContain('.insight-products strong { display: block; overflow-wrap: anywhere;')
    expect(css).not.toContain('.insight-products strong { display: block; overflow: hidden;')
  })
})
