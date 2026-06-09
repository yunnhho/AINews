'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getRecommended } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import type { Card } from '@/lib/types'
import CardItem from '@/components/cards/CardItem'
import { CardSkeletonList } from '../(feed)/components/CardSkeleton'

function todayLine(): string {
  return new Date().toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
}

export default function RecommendedPage() {
  const token = useAuthStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)
  const [items, setItems] = useState<Card[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const unsub = useAuthStore.persist.onFinishHydration(() => setHydrated(true))
    if (useAuthStore.persist.hasHydrated()) setHydrated(true)
    return unsub
  }, [])

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setError(false)
    getRecommended(token, 30)
      .then((d) => !cancelled && setItems(d.items))
      .catch(() => !cancelled && setError(true))
    return () => {
      cancelled = true
    }
  }, [token])

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6">
      {/* ── 에디토리얼 마스트헤드 ── */}
      <header className="pt-8 pb-5 animate-rise">
        <div className="flex items-center gap-3 mb-3">
          <span className="label-kicker text-accent">For You · 셀렉션</span>
          <span className="flex-1 h-px bg-rule" />
          <span className="font-mono text-[11px] text-ink-faint">{todayLine()}</span>
        </div>
        <h1 className="font-serif text-[2rem] sm:text-[2.5rem] font-extrabold leading-[1.05] tracking-[-0.02em] text-ink">
          당신의 취향으로
          <br />
          고른 오늘의 카드
        </h1>
        <p className="mt-3 max-w-prose text-[0.875rem] leading-relaxed text-ink-soft">
          좋아요와 북마크를 남긴 카드를 토대로, 결이 비슷한 독자들이 아낀 글을 함께
          추려 보여드립니다. 더 많이 읽고 반응할수록 추천은 당신에게 가까워집니다.
        </p>
        <div className="mt-4 h-px bg-ink" />
      </header>

      {/* ── 본문 ── */}
      <div className="pb-16">
        {hydrated && !token && (
          <EmptyState
            title="로그인하면 추천이 시작돼요"
            body="좋아요·북마크 몇 개만 남겨도 당신을 위한 셀렉션이 만들어집니다."
            cta={{ href: '/', label: '카드 둘러보기' }}
          />
        )}

        {token && items === null && !error && (
          <div className="pt-2">
            <CardSkeletonList count={4} />
          </div>
        )}

        {token && error && (
          <p className="py-16 text-center text-sm text-accent-ink">
            추천을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.
          </p>
        )}

        {token && items !== null && items.length === 0 && (
          <EmptyState
            title="아직 추천할 카드가 모자라요"
            body="마음에 드는 카드에 좋아요나 북마크를 남겨 주세요. 취향이 쌓이면 이 자리가 채워집니다."
            cta={{ href: '/', label: '피드로 가기' }}
          />
        )}

        {token && items !== null && items.length > 0 && (
          <ol className="flex flex-col">
            {items.map((card, i) => (
              <li
                key={card.id}
                className="flex gap-4 py-4 first:pt-5 rule-t first:border-t-0 animate-rise"
                style={{ animationDelay: `${Math.min(i, 8) * 45}ms` }}
              >
                <span className="font-serif text-[1.5rem] font-bold text-rule leading-none pt-1 select-none w-8 shrink-0 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div className="flex-1 min-w-0">
                  <CardItem card={card} />
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}

function EmptyState({
  title,
  body,
  cta,
}: {
  title: string
  body: string
  cta: { href: string; label: string }
}) {
  return (
    <div className="py-16 text-center max-w-sm mx-auto">
      <p className="font-serif text-xl font-bold text-ink mb-2">{title}</p>
      <p className="text-sm text-ink-soft leading-relaxed mb-5">{body}</p>
      <Link
        href={cta.href}
        className="label-kicker inline-block text-paper bg-ink px-4 py-2 hover:bg-accent transition-colors"
      >
        {cta.label}
      </Link>
    </div>
  )
}
