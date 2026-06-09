'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { searchCards } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { Card } from '@/lib/types'
import CardItem from '@/components/cards/CardItem'
import { CardSkeletonList } from '../(feed)/components/CardSkeleton'

function SearchView() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = useAuthStore((s) => s.token)

  const initialQ = searchParams.get('q') ?? ''
  const [input, setInput] = useState(initialQ)
  const [query, setQuery] = useState(initialQ)
  const [items, setItems] = useState<Card[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  // URL의 q가 바뀌면 검색어 동기화
  useEffect(() => {
    setQuery(initialQ)
    setInput(initialQ)
  }, [initialQ])

  useEffect(() => {
    const q = query.trim()
    if (!q) {
      setItems(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(false)
    searchCards(q, { limit: 20 }, token ?? undefined)
      .then((data) => {
        if (!cancelled) setItems(data.items)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [query, token])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const q = input.trim()
    setQuery(q)
    router.replace(q ? `/search?q=${encodeURIComponent(q)}` : '/search')
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <h1 className="text-xl font-bold text-gray-900 mb-3">검색</h1>

      <form onSubmit={submit} className="flex gap-0 mb-6 border-b-2 border-ink">
        <input
          autoFocus
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="제목·요약·태그 검색 — 한국어·English 지원"
          className="flex-1 bg-transparent px-1 py-2.5 text-base text-ink placeholder:text-ink-faint focus:outline-none"
        />
        <button
          type="submit"
          className="label-kicker px-4 py-2 bg-ink text-paper hover:bg-accent transition-colors self-center"
        >
          검색
        </button>
      </form>

      {!query && (
        <p className="text-center text-sm text-gray-400 py-16">검색어를 입력해 주세요.</p>
      )}

      {query && loading && <CardSkeletonList count={3} />}

      {query && error && (
        <p className="text-center text-sm text-red-500 py-12">
          검색에 실패했어요. 잠시 후 다시 시도해 주세요.
        </p>
      )}

      {query && !loading && !error && items !== null && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-sm">&lsquo;{query}&rsquo; 검색 결과가 없어요.</p>
        </div>
      )}

      {query && items !== null && items.length > 0 && (
        <>
          <p className="label-kicker text-ink-faint mb-3">{items.length}개 결과</p>
          <div className="flex flex-col gap-3">
            {items.map((card) => (
              <CardItem key={card.id} card={card} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="max-w-2xl mx-auto px-4 py-8 text-sm text-gray-400">로딩 중…</div>}>
      <SearchView />
    </Suspense>
  )
}
