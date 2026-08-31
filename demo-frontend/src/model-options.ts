export const BUILT_IN_MODEL_PRESETS = [
  'deepseek-v4-flash',
  'deepseek-v4-pro',
] as const

export const CUSTOM_MODEL_VALUE = '__custom__'

export function mergeModelPresets(apiPresets: string[] = []): string[] {
  return Array.from(new Set([
    ...BUILT_IN_MODEL_PRESETS,
    ...apiPresets.filter(Boolean),
  ]))
}
