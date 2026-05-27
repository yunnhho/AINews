'use client'

import { useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import AuthModal from './AuthModal'

export default function HeaderAuth() {
  const { user, logout } = useAuthStore()
  const [showAuth, setShowAuth] = useState(false)

  if (user) {
    return (
      <div className="flex items-center gap-2">
        {user.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.avatar_url}
            alt={user.nickname}
            className="w-7 h-7 rounded-full object-cover"
          />
        ) : (
          <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center text-xs font-bold text-gray-600">
            {user.nickname.slice(0, 1).toUpperCase()}
          </div>
        )}
        <span className="text-sm text-gray-700 hidden sm:block">{user.nickname}</span>
        <button
          onClick={logout}
          className="text-xs text-gray-400 hover:text-gray-700 transition-colors ml-1"
        >
          로그아웃
        </button>
      </div>
    )
  }

  return (
    <>
      <button
        onClick={() => setShowAuth(true)}
        className="text-sm font-medium text-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
      >
        로그인
      </button>
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} />
    </>
  )
}
