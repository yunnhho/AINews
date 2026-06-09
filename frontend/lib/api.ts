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

// 인증이 필요한 요청이 401을 받으면(주로 토큰 만료) 호출되는 전역 핸들러.
// 스토어 모듈에서 등록해 만료 토큰을 정리(로그아웃)하고 UI를 실제 상태로 되돌린다.
let unauthorizedHandler: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn
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
    // 토큰을 보냈는데 401이면 만료/무효 토큰이다. 전역 핸들러로 로그아웃 처리.
    if (res.status === 401 && token) unauthorizedHandler?.()
    const body = await res.json().catch(() => ({}))
    const err = (body as { error?: { code?: string; message?: string } })?.error ?? {}
    throw new ApiError(err.code ?? 'UNKNOWN', err.message ?? res.statusText, res.status)
  }

  // 204 No Content(좋아요/북마크 등) 또는 빈 본문은 JSON 파싱하지 않는다.
  if (res.status === 204 || res.headers.get('content-length') === '0') {
    return undefined as T
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

// ── 개인화 추천 (인증 필수) ──────────────────────────────────────────────────

export function getRecommended(token: string, limit = 20): Promise<FeedResponse> {
  return request<FeedResponse>(`/cards/recommended?limit=${limit}`, { cache: 'no-store', token })
}

// ── 내 북마크 (인증 필수) ────────────────────────────────────────────────────

export function getMyBookmarks(token: string, params: FeedParams = {}): Promise<FeedResponse> {
  const qs = new URLSearchParams()
  if (params.category && params.category !== 'all') qs.set('category', params.category)
  if (params.card_type && params.card_type !== 'all') qs.set('card_type', params.card_type)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))

  const query = qs.size ? `?${qs}` : ''
  return request<FeedResponse>(`/me/bookmarks${query}`, { cache: 'no-store', token })
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
