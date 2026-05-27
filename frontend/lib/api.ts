import type { Card, FeedParams, FeedResponse } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  { token, ...init }: RequestInit & { token?: string } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = (body as { error?: { code?: string; message?: string } })?.error ?? {}
    throw new ApiError(err.code ?? 'UNKNOWN', err.message ?? res.statusText, res.status)
  }

  return res.json() as Promise<T>
}

// ── 카드 ──────────────────────────────────────────────────────────────────────

export function getCards(params: FeedParams = {}, token?: string): Promise<FeedResponse> {
  const qs = new URLSearchParams()
  if (params.category && params.category !== 'all') qs.set('category', params.category)
  if (params.card_type && params.card_type !== 'all') qs.set('card_type', params.card_type)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  params.tags?.forEach((t) => qs.append('tags', t))

  const query = qs.size ? `?${qs}` : ''
  return request<FeedResponse>(`/cards${query}`, { cache: 'no-store', token })
}

export function getCard(id: number, token?: string): Promise<Card> {
  return request<Card>(`/cards/${id}`, { cache: 'no-store', token })
}

// ── 좋아요 / 북마크 (인증 필수) ──────────────────────────────────────────────

export function likeCard(id: number, token: string) {
  return request(`/cards/${id}/like`, { method: 'POST', token })
}

export function unlikeCard(id: number, token: string) {
  return request(`/cards/${id}/like`, { method: 'DELETE', token })
}

export function bookmarkCard(id: number, token: string) {
  return request(`/cards/${id}/bookmark`, { method: 'POST', token })
}

export function unbookmarkCard(id: number, token: string) {
  return request(`/cards/${id}/bookmark`, { method: 'DELETE', token })
}

// ── 검색 ──────────────────────────────────────────────────────────────────────

export function searchCards(
  q: string,
  params: Pick<FeedParams, 'category' | 'card_type'> & { limit?: number } = {},
  token?: string,
): Promise<FeedResponse> {
  const qs = new URLSearchParams({ q })
  if (params.category) qs.set('category', params.category)
  if (params.card_type) qs.set('card_type', params.card_type)
  if (params.limit) qs.set('limit', String(params.limit))
  return request<FeedResponse>(`/search?${qs}`, { cache: 'no-store', token })
}
