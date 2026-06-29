'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { fetchMe, logoutRequest, setUnauthorizedHandler } from '@/lib/api'

export interface AuthUser {
  id: number
  nickname: string
  avatar_url: string | null
}

interface AuthState {
  // 토큰은 HttpOnly 쿠키에만 존재한다. 프론트는 비민감 프로필만 보관한다.
  user: AuthUser | null
  setUser: (user: AuthUser | null) => void
  refreshUser: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      // 쿠키 세션의 실제 상태를 /auth/me로 확인해 프로필을 동기화한다.
      refreshUser: async () => {
        try {
          const me = await fetchMe()
          set({ user: { id: me.id, nickname: me.nickname, avatar_url: me.avatar_url } })
        } catch {
          set({ user: null })
        }
      },
      // 서버에서 refresh token 폐기 + 쿠키 삭제 후 로컬 상태 정리.
      logout: async () => {
        try {
          await logoutRequest()
        } catch {
          // 네트워크 오류여도 로컬 상태는 비운다.
        }
        set({ user: null })
      },
    }),
    {
      name: 'ai-pulse-auth',
      // 토큰은 저장하지 않는다 — 비민감 프로필만 영속화한다.
      partialize: (state) => ({ user: state.user }),
    },
  ),
)

// 인증 요청이 401을 받으면(세션 만료 등) 로컬 로그인 상태를 비운다.
if (typeof window !== 'undefined') {
  setUnauthorizedHandler(() => useAuthStore.setState({ user: null }))
}
