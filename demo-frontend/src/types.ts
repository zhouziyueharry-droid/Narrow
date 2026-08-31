export type Provider = 'local' | 'deepseek'
export type EvaluationMode = 'native' | 'simulator-techjam' | 'simulator-realistic'
export type JobStatus = 'queued' | 'running' | 'finalizing_diagnostics' | 'completed' | 'failed' | 'cancelled' | 'interrupted'

export interface Capabilities {
  catalog: { available: boolean; product_count: number; bytes: number }
  public_set: { available: boolean; session_count: number }
  deepseek_configured: boolean
  trace_url: string
  limits: Record<EvaluationMode, number>
}

export interface Settings {
  reranker?: 'precise' | 'lambdamart'
  provider: Provider
  model: string
  base_url: string
  realistic_verbalizer: 'template' | 'deepseek'
  revision: number
  deepseek_configured: boolean
  model_presets: string[]
}

export interface Job {
  protected?: boolean
  id: string
  mode: EvaluationMode
  status: JobStatus
  code: string
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  config: {
    count: number
    provider: Provider
    model: string
    realistic_verbalizer: 'template' | 'deepseek'
    seed: number
  }
  progress: { completed: number; total: number }
  metrics?: Record<string, any> | null
  error?: { code: string; detail?: string } | null
}

export interface RunDeleteResult {
  deleted: string[]
  not_found: string[]
}

export interface ConversationTurn {
  turn: number
  user: string
  assistant: string
  ask_attribute?: string | null
  recommendations: string[]
  target_rank?: number | null
  latency_ms?: number | null
  usage?: Record<string, number>
  intent?: Record<string, any>
  user_dialogue_act?: Record<string, any>
  next_dialogue_act?: string | null
  error?: string | null
}

export interface EvaluationSession {
  id: string
  sample_id: string
  scenario: string
  hit: boolean
  success: boolean
  first_hit_turn?: number | null
  best_rank?: number | null
  turn_count: number
  target?: Record<string, any> | null
  target_parent_asin?: string | null
  goal?: Record<string, any>
  persona?: string | null
  acceptance?: Record<string, any>
  errors: string[]
  conversation: ConversationTurn[]
}

export interface EvaluationResult {
  mode: EvaluationMode
  metrics: Record<string, any>
  sessions: EvaluationSession[]
  partial?: boolean
  completed_sessions?: number
  total_sessions?: number
  generated_at?: string
}

export interface Recommendation {
  parent_asin: string
  score?: number | null
  title: string
  brand?: string | null
  price?: number | null
  rating?: number | null
  rating_number?: number | null
  categories: string[]
  features: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
  ask_attribute?: string | null
  usage?: Record<string, number>
  recommendations?: Recommendation[]
  intent?: Record<string, any>
  latency_ms?: number
  provider?: Provider
  model?: string | null
}

export interface ChatSession {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages: ChatMessage[]
  settings_revision: number
  message_count?: number
}
