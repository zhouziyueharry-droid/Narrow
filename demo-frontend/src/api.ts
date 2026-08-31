export class ApiError extends Error {
  code: string
  status: number
  detail?: string

  constructor(code: string, status: number, detail?: string) {
    super(code)
    this.code = code
    this.status = status
    this.detail = detail
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(
      data?.error?.code ?? 'unknown',
      response.status,
      data?.error?.detail,
    )
  }
  return data as T
}

export function diagnosticUrl(
  traceBase: string,
  runId: string,
  sessionId: string,
  turn: number | undefined,
  locale: string,
  mode: 'target' | 'agent',
) {
  const url = new URL(traceBase)
  url.searchParams.set('runId', runId)
  url.searchParams.set('session', sessionId)
  if (turn) url.searchParams.set('turn', String(turn))
  url.searchParams.set('diagnosticMode', mode)
  url.searchParams.set('lang', locale)
  const returnUrl = new URL(window.location.href)
  returnUrl.searchParams.set('lang', locale)
  url.searchParams.set('returnUrl', returnUrl.toString())
  return url.toString()
}
