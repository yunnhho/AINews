'use client'

import { Suspense, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuthStore } from '@/stores/auth'

function CallbackHandler() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)

  useEffect(() => {
    const token = searchParams.get('access_token')
    const userId = Number(searchParams.get('user_id') ?? 0)
    const nickname = searchParams.get('nickname') ?? ''
    const avatarUrl = searchParams.get('avatar_url') || null

    if (token && userId) {
      setAuth(token, { id: userId, nickname, avatar_url: avatarUrl })
    }
    router.replace('/')
  }, [searchParams, setAuth, router])

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
