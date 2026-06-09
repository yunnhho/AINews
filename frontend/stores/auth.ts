'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { setUnauthorizedHandler } from '@/lib/api'

export interface AuthUser {
  id: number
  nickname: string
  avatar_url: string | null
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  logout: () => void
}

// JWT exp(초)를 디코드해 만료 여부를 판단한다. 형식이 깨졌으면 만료로 간주.
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (typeof payload.exp !== 'number') return false
    return payload.exp * 1000 <= Date.now()
  } catch {
    return true
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'ai-pulse-auth',
      // 새로고침으로 저장된 토큰을 복원할 때 이미 만료됐으면 즉시 비운다.
      // (만료 토큰으로 로그인 상태처럼 보이지만 모든 인증 동작이 401로 실패하는 버그 방지)
      onRehydrateStorage: () => (state) => {
        if (state?.token && isTokenExpired(state.token)) {
          state.token = null
          state.user = null
        }
      },
    },
  ),
)

// 인증 요청이 401을 받으면(세션 중 만료 등) 스토어를 비워 UI를 실제 상태로 되돌린다.
if (typeof window !== 'undefined') {
  setUnauthorizedHandler(() => useAuthStore.getState().logout())
}
