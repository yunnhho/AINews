import type { Card, FeedParams, FeedResponse } from '@/lib/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

export interface MeResponse {
  id: number
  provider: string
  nickname: string
  avatar_url: string | null
}

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

// 인증이 필요한 요청이 401을 받으면(주로 세션 만료) 호출되는 전역 핸들러.
// 스토어 모듈에서 등록해 로그인 상태를 정리하고 UI를 실제 상태로 되돌린다.
let unauthorizedHandler: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

// 더블 서브밋 CSRF — 백엔드가 내려준 비-HttpOnly csrf_token 쿠키를 읽어 헤더로 되돌려보낸다.
function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'))
  return match ? decodeURIComponent(match[1]) : null
}

export function csrfHeader(): Record<string, string> {
  const csrf = readCookie('csrf_token')
  return csrf ? { 'X-CSRF-Token': csrf } : {}
}

// access token이 만료되면 refresh 쿠키로 조용히 재발급한다. 동시 401을 한 번으로 합친다.
let refreshing: Promise<boolean> | null = null
export function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: csrfHeader(),
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshing = null
      })
  }
  return refreshing
}

async function request<T>(path: string, init: RequestInit = {}, retried = false): Promise<T> {
  const headers = new Headers(init.headers)
  const method = (init.method ?? 'GET').toUpperCase()
  if (init.body) headers.set('Content-Type', 'application/json')
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie('csrf_token')
    if (csrf) headers.set('X-CSRF-Token', csrf)
  }

  // 인증은 HttpOnly 쿠키로 전달되므로 credentials: 'include' 필수.
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })

  // access 만료(401) 시 1회에 한해 refresh 후 원요청을 재시도한다.
  // (refresh/logout 자신은 재귀를 피하기 위해 제외)
  const isAuthFlow = path.startsWith('/auth/refresh') || path.startsWith('/auth/logout')
  if (res.status === 401 && !retried && !isAuthFlow) {
    if (await tryRefresh()) return request<T>(path, init, true)
  }

  if (!res.ok) {
    // 인증이 필요한 요청에서 401이면 세션이 만료/무효다. 전역 핸들러로 로그아웃 처리.
    if (res.status === 401) unauthorizedHandler?.()
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

// ── 인증 ────────────────────────────────────────────────────────────────────────

export function fetchMe(): Promise<MeResponse> {
  return request<MeResponse>('/auth/me', { cache: 'no-store' })
}

export function logoutRequest(): Promise<void> {
  return request<void>('/auth/logout', { method: 'DELETE' })
}

// ── 카드 ──────────────────────────────────────────────────────────────────────

export function getCards(params: FeedParams = {}): Promise<FeedResponse> {
  const qs = new URLSearchParams()
  if (params.category && params.category !== 'all') qs.set('category', params.category)
  if (params.card_type && params.card_type !== 'all') qs.set('card_type', params.card_type)
  if (params.difficulty) qs.set('difficulty', params.difficulty)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))
  params.tags?.forEach((t) => qs.append('tags', t))

  const query = qs.size ? `?${qs}` : ''
  return request<FeedResponse>(`/cards${query}`, { cache: 'no-store' })
}

export function getCard(id: number): Promise<Card> {
  return request<Card>(`/cards/${id}`, { cache: 'no-store' })
}

// ── 좋아요 / 북마크 (인증 필수) ──────────────────────────────────────────────

export function likeCard(id: number) {
  return request(`/cards/${id}/like`, { method: 'POST' })
}

export function unlikeCard(id: number) {
  return request(`/cards/${id}/like`, { method: 'DELETE' })
}

export function bookmarkCard(id: number) {
  return request(`/cards/${id}/bookmark`, { method: 'POST' })
}

export function unbookmarkCard(id: number) {
  return request(`/cards/${id}/bookmark`, { method: 'DELETE' })
}

// ── 개인화 추천 (인증 필수) ──────────────────────────────────────────────────

export function getRecommended(limit = 20): Promise<FeedResponse> {
  return request<FeedResponse>(`/cards/recommended?limit=${limit}`, { cache: 'no-store' })
}

// ── 내 북마크 (인증 필수) ────────────────────────────────────────────────────

export function getMyBookmarks(params: FeedParams = {}): Promise<FeedResponse> {
  const qs = new URLSearchParams()
  if (params.category && params.category !== 'all') qs.set('category', params.category)
  if (params.card_type && params.card_type !== 'all') qs.set('card_type', params.card_type)
  if (params.cursor) qs.set('cursor', params.cursor)
  if (params.limit) qs.set('limit', String(params.limit))

  const query = qs.size ? `?${qs}` : ''
  return request<FeedResponse>(`/me/bookmarks${query}`, { cache: 'no-store' })
}

// ── 검색 ──────────────────────────────────────────────────────────────────────

export function searchCards(
  q: string,
  params: Pick<FeedParams, 'category' | 'card_type'> & { limit?: number } = {},
): Promise<FeedResponse> {
  const qs = new URLSearchParams({ q })
  if (params.category) qs.set('category', params.category)
  if (params.card_type) qs.set('card_type', params.card_type)
  if (params.limit) qs.set('limit', String(params.limit))
  return request<FeedResponse>(`/search?${qs}`, { cache: 'no-store' })
}
