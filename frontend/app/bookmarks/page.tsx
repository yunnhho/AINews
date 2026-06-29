'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMyBookmarks } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { Card } from '@/lib/types'
import CardItem from '@/components/cards/CardItem'
import { CardSkeletonList } from '../(feed)/components/CardSkeleton'

export default function BookmarksPage() {
  const user = useAuthStore((s) => s.user)
  const [items, setItems] = useState<Card[] | null>(null)
  const [error, setError] = useState(false)
  // zustand persist 재수화 전에는 user가 잠깐 null일 수 있어 1프레임 기다린다.
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setReady(true), 0)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    setError(false)
    getMyBookmarks({ limit: 50 })
      .then((data) => {
        if (!cancelled) setItems(data.items)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
    return () => {
      cancelled = true
    }
  }, [user])

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <h1 className="text-xl font-bold text-gray-900 mb-4">내 북마크</h1>

      {ready && !user && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <p className="text-4xl mb-3">🔖</p>
          <p className="text-sm">로그인 후 북마크한 카드를 볼 수 있어요.</p>
          <Link href="/" className="mt-4 text-sm font-medium text-blue-600 hover:underline">
            홈으로 가기
          </Link>
        </div>
      )}

      {user && items === null && !error && <CardSkeletonList count={4} />}

      {user && error && (
        <p className="text-center text-sm text-red-500 py-12">
          북마크를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
        </p>
      )}

      {user && items !== null && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <p className="text-4xl mb-3">🔖</p>
          <p className="text-sm">아직 북마크한 카드가 없어요.</p>
          <Link href="/" className="mt-4 text-sm font-medium text-blue-600 hover:underline">
            카드 둘러보기
          </Link>
        </div>
      )}

      {user && items !== null && items.length > 0 && (
        <div className="flex flex-col gap-3">
          {items.map((card) => (
            <CardItem key={card.id} card={card} />
          ))}
        </div>
      )}
    </div>
  )
}
