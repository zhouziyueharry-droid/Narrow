import type { EvaluationMode } from '@/types'

export function evaluationLimit(mode: EvaluationMode) {
  return mode === 'simulator-realistic' ? 100 : 200
}

export function isValidSessionCount(mode: EvaluationMode, count: number) {
  return Number.isInteger(count) && count >= 1 && count <= evaluationLimit(mode)
}

export function evaluationRunQuery(
  currentQuery: Record<string, unknown>,
  runId: string,
  locale: string,
) {
  return { ...currentQuery, runId, lang: locale }
}
