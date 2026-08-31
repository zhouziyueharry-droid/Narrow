export const DEFAULT_INLINE_RECOMMENDATIONS = 4
export const MAX_INLINE_RECOMMENDATIONS = 10

export function inlineRecommendationLimit(expanded: boolean) {
  return expanded ? MAX_INLINE_RECOMMENDATIONS : DEFAULT_INLINE_RECOMMENDATIONS
}

export function hiddenRecommendationCount(total: number) {
  return Math.max(
    0,
    Math.min(total, MAX_INLINE_RECOMMENDATIONS) - DEFAULT_INLINE_RECOMMENDATIONS,
  )
}
