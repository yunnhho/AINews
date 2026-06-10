'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'

const NAV = [
  { href: '/admin', label: '대시보드', icon: '📊' },
  { href: '/admin/batches', label: '배치 이력', icon: '🔄' },
  { href: '/admin/sources', label: '소스 관리', icon: '📡' },
  { href: '/admin/translation', label: '번역 큐', icon: '🌐' },
  { href: '/admin/costs', label: '비용 현황', icon: '💰' },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore()
  const router = useRouter()
  const pathname = usePathname()
  // zustand persist 재수화 완료 전에는 token이 null이라, 재수화를 기다린 뒤에만
  // 미로그인 리다이렉트를 판단한다. (그렇지 않으면 새로고침 시 항상 홈으로 튕긴다.)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    if (useAuthStore.persist.hasHydrated()) setHydrated(true)
    return unsub
  }, [])

  useEffect(() => {
    if (hydrated && !token) router.replace('/')
  }, [hydrated, token, router])

  if (!hydrated) return null
  if (!token) return null

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* 사이드바 */}
      <aside className="w-52 flex-shrink-0 bg-white border-r border-gray-200 pt-14">
        <nav className="p-3 space-y-1">
          {NAV.map(({ href, label, icon }) => {
            const isActive = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-100',
                )}
              >
                <span>{icon}</span>
                {label}
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* 메인 — 루트 레이아웃의 <main> 안에 중첩되므로 section 사용 */}
      <section className="flex-1 pt-14 overflow-auto">
        <div className="max-w-5xl mx-auto p-6">{children}</div>
      </section>
    </div>
  )
}
