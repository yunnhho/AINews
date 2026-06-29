'use client'

import { Suspense, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'

function CallbackHandler() {
  const router = useRouter()
  const refreshUser = useAuthStore((s) => s.refreshUser)

  useEffect(() => {
    // 백엔드가 HttpOnly 쿠키로 세션을 설정한 뒤 이 페이지로 리다이렉트한다.
    // 토큰은 URL에 없으며, /auth/me로 프로필만 받아 스토어를 채운다.
    refreshUser().finally(() => router.replace('/'))
  }, [refreshUser, router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-sm text-gray-500">로그인 처리 중…</p>
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen">
          <p className="text-sm text-gray-500">로딩 중…</p>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  )
}
