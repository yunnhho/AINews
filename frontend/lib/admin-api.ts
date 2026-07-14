import { csrfHeader, tryRefresh } from '@/lib/api'

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
  status: 'critical' | 'warning'
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

async function adminFetch<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const method = (init?.method ?? 'GET').toUpperCase()
  if (method !== 'GET') Object.assign(headers, csrfHeader())
  // 인증은 HttpOnly 쿠키로 전달된다.
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
    credentials: 'include',
  })
  // access 만료(401) 시 1회 refresh 후 재시도.
  if (res.status === 401 && !retried && (await tryRefresh())) {
    return adminFetch<T>(path, init, true)
  }
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json() as Promise<T>
}

export const adminApi = {
  getMetrics: () => adminFetch<AdminMetrics>('/admin/metrics'),
  getBatches: () => adminFetch<{ items: BatchLog[] }>('/admin/batches'),
  getSourceHealth: () => adminFetch<{ items: SourceHealth[] }>('/admin/sources/health'),
  toggleSource: (sourceId: number, enabled: boolean) =>
    adminFetch(`/admin/sources/${sourceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    }),
  getTranslationQueue: () =>
    adminFetch<{ items: TranslationItem[] }>('/admin/translation-queue'),
  reviewTranslation: (logId: number, action: 'approve' | 'reject') =>
    adminFetch(`/admin/translation-queue/${logId}`, {
      method: 'PATCH',
      body: JSON.stringify({ action }),
    }),
}
