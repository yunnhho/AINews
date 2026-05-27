'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { getCards } from '@/lib/api'
import type { Card, FeedParams } from '@/lib/types'
import CardItem from '@/components/cards/CardItem'
import { CardSkeletonList } from './CardSkeleton'

interface Props {
  initialItems: Card[]
  initialCursor: string | null
  initialHasMore: boolean
  filterKey: string  // 필터 변경 시 key로 리셋 트리거 (page.tsx에서 주입)
  params: Pick<FeedParams, 'category' | 'card_type' | 'tags'>
}

export default function InfiniteCardList({
  initialItems,
  initialCursor,
  initialHasMore,
  params,
}: Props) {
  const [items, setItems] = useState<Card[]>(initialItems)
  const [cursor, setCursor] = useState<string | null>(initialCursor)
  const [hasMore, setHasMore] = useState(initialHasMore)
  const [isLoading, setIsLoading] = useState(false)
  const sentinelRef = useRef<HTMLDivElement>(null)

  // initialItems가 바뀌면 (필터 변경) 상태 리셋
  useEffect(() => {
    setItems(initialItems)
    setCursor(initialCursor)
    setHasMore(initialHasMore)
  }, [initialItems, initialCursor, initialHasMore])

  const loadMore = useCallback(async () => {
    if (isLoading || !hasMore || !cursor) return
    setIsLoading(true)
    try {
      const data = await getCards({ ...params, cursor, limit: 20 })
      setItems((prev) => [...prev, ...data.items])
      setCursor(data.next_cursor)
      setHasMore(data.has_more)
    } catch {
      // 네트워크 오류 시 조용히 실패 (다음 스크롤 시 재시도)
    } finally {
      setIsLoading(false)
    }
  }, [isLoading, hasMore, cursor, params])

  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) loadMore()
      },
      { rootMargin: '200px' },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [loadMore])

  if (items.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400">
        <p className="text-4xl mb-3">🤖</p>
        <p className="text-sm">아직 카드가 없습니다.</p>
        <p className="text-xs mt-1">첫 배치 후 자동으로 채워집니다.</p>
      </div>
    )
  }

  return (
    <>
      <div className="flex flex-col gap-3 px-4 py-3">
        {items.map((card) => (
          <CardItem key={card.id} card={card} />
        ))}
      </div>

      {/* 무한 스크롤 센티넬 */}
      <div ref={sentinelRef} className="h-4" />

      {isLoading && <CardSkeletonList count={3} />}

      {!hasMore && items.length > 0 && (
        <p className="text-center text-xs text-gray-400 py-8">모든 카드를 불러왔습니다.</p>
      )}
    </>
  )
}
