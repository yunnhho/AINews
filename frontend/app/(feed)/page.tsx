import { Suspense } from 'react'
import { getCards } from '@/lib/api'
import type { Tag } from '@/lib/types'
import CategoryTabs from './components/CategoryTabs'
import TypeFilter from './components/TypeFilter'
import TagChips from './components/TagChips'
import InfiniteCardList from './components/InfiniteCardList'
import { CardSkeletonList } from './components/CardSkeleton'

type SearchParams = Promise<{
  category?: string
  card_type?: string
  tags?: string | string[]
}>

export default async function FeedPage({ searchParams }: { searchParams: SearchParams }) {
  const sp = await searchParams

  const category = sp.category ?? 'all'
  const cardType = sp.card_type ?? 'all'
  const tags = sp.tags ? (Array.isArray(sp.tags) ? sp.tags : [sp.tags]) : []

  // SSR 초기 데이터 (실패 시 빈 피드)
  const initial = await getCards({ category, card_type: cardType, tags, limit: 20 }).catch(() => ({
    items: [],
    next_cursor: null,
    has_more: false,
  }))

  // 태그 칩: 현재 피드 아이템에서 추출 (최대 15개)
  const tagMap = new Map<string, Tag>()
  for (const card of initial.items) {
    for (const tag of card.tags) {
      if (!tagMap.has(tag.slug)) tagMap.set(tag.slug, tag)
      if (tagMap.size >= 15) break
    }
  }
  const availableTags = Array.from(tagMap.values())

  // 필터 변경 시 InfiniteCardList 리셋용 키
  const filterKey = `${category}-${cardType}-${tags.sort().join(',')}`

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6">
      <div className="flex items-baseline gap-3 pt-7 pb-3">
        <h1 className="font-serif text-[1.75rem] font-extrabold tracking-[-0.02em] text-ink">
          오늘의 피드
        </h1>
        <span className="label-kicker text-ink-faint">Latest</span>
      </div>
      <Suspense>
        <CategoryTabs active={category} />
        <TypeFilter active={cardType} />
        {availableTags.length > 0 && <TagChips tags={availableTags} activeSlugs={tags} />}
      </Suspense>

      <InfiniteCardList
        key={filterKey}
        filterKey={filterKey}
        initialItems={initial.items}
        initialCursor={initial.next_cursor}
        initialHasMore={initial.has_more}
        params={{ category, card_type: cardType, tags }}
      />
    </div>
  )
}
