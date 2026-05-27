const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

export interface BatchLog {
  id: number
  batch_id: string
  scheduled_at: string
  started_at: string | null
  completed_at: string | null
  status: 'SCHEDULED' | 'RUNNING' | 'COMPLETED' | 'PARTIAL_FAILURE' | 'FAILED'
  collected_by_group: Record<string, number> | null
  deduplicated_count: number
  published_by_type: Record<string, number> | null
  failed_count: number
  api_tokens_used: number
  api_cost_usd: number
  error_log: string | null
}

export interface SourceHealth {
  source_id: number
  source_name: string
  source_group: string
  last_success_at: string | null
  consecutive_failures: number
  last_error_log: string | null
  enabled: boolean
}

export interface TranslationItem {
  id: number
  card_id: number
  original_text: string
  translated_text: string
  back_translated_text: string | null
  similarity_score: number | null
  passed: boolean
  retry_count: number
  created_at: string
}

export interface AdminMetrics {
  today_published: Record<string, number>
  batch_success_rate_7d: number
  translation_pass_rate: number
  monthly_api_cost_usd: number
  monthly_budget_usd: number
  alert_sources: SourceHealth[]
  daily_costs: { date: string; cost_usd: number }[]
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}

export const adminApi = {
  getMetrics: (token: string) => adminFetch<AdminMetrics>('/admin/metrics', token),
  getBatches: (token: string) => adminFetch<{ items: BatchLog[] }>('/admin/batches', token),
  getSourceHealth: (token: string) =>
    adminFetch<{ items: SourceHealth[] }>('/admin/sources/health', token),
  toggleSource: (sourceId: number, enabled: boolean, token: string) =>
    adminFetch(`/admin/sources/${sourceId}`, token, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    }),
  getTranslationQueue: (token: string) =>
    adminFetch<{ items: TranslationItem[] }>('/admin/translation-queue', token),
}
