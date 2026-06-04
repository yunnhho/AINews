import axios from 'axios'
import type { Card, FeedParams, FeedResponse, UserProfile } from './types'

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

const client = axios.create({ baseURL: BASE_URL })

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` }
}

export const api = {
  getCards: (params: FeedParams = {}, token?: string) =>
    client
      .get<FeedResponse>('/cards', {
        params,
        headers: token ? authHeader(token) : undefined,
      })
      .then((r) => r.data),

  getCard: (id: number, token?: string) =>
    client
      .get<Card>(`/cards/${id}`, {
        headers: token ? authHeader(token) : undefined,
      })
      .then((r) => r.data),

  getBookmarks: (token: string, category?: string) =>
    client
      .get<FeedResponse>('/me/bookmarks', {
        params: category ? { category } : undefined,
        headers: authHeader(token),
      })
      .then((r) => r.data),

  getMe: (token: string) =>
    client
      .get<UserProfile>('/auth/me', { headers: authHeader(token) })
      .then((r) => r.data),

  likeCard: (id: number, token: string) =>
    client.post(`/cards/${id}/like`, null, { headers: authHeader(token) }),

  unlikeCard: (id: number, token: string) =>
    client.delete(`/cards/${id}/like`, { headers: authHeader(token) }),

  bookmarkCard: (id: number, token: string) =>
    client.post(`/cards/${id}/bookmark`, null, { headers: authHeader(token) }),

  unbookmarkCard: (id: number, token: string) =>
    client.delete(`/cards/${id}/bookmark`, { headers: authHeader(token) }),

  registerPushToken: (authToken: string, expoPushToken: string) =>
    client.post(
      '/push/register',
      { expo_push_token: expoPushToken },
      { headers: authHeader(authToken) }
    ),

  togglePushNotifications: (authToken: string, expoPushToken: string, enabled: boolean) =>
    client.patch(
      '/push/notifications',
      { expo_push_token: expoPushToken, enabled },
      { headers: authHeader(authToken) }
    ),

  exchangeAuthCode: (code: string) =>
    client
      .post<{ access_token: string; refresh_token: string; expires_in: number }>(
        '/auth/exchange',
        { code },
      )
      .then((r) => r.data),
}
