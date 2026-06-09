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
            className="w-6 h-6 object-cover border border-ink/20"
          />
        ) : (
          <div className="w-6 h-6 bg-ink flex items-center justify-center text-[11px] font-bold text-paper">
            {user.nickname.slice(0, 1).toUpperCase()}
          </div>
        )}
        <span className="text-[13px] text-ink hidden sm:block">{user.nickname}</span>
        <button
          onClick={logout}
          className="label-kicker text-ink-faint hover:text-ink transition-colors ml-1"
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
        className="label-kicker text-paper bg-ink px-3 py-1.5 hover:bg-accent transition-colors"
      >
        로그인
      </button>
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} />
    </>
  )
}
