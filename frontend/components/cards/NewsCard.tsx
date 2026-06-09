'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import type { NewsCard as NewsCardType } from '@/lib/types'
import { TypeBadge, CategoryBadge, DifficultyBadge } from './CardBadges'
import NewsCardExpanded from './NewsCardExpanded'

interface Props {
  card: NewsCardType
}

export default function NewsCard({ card }: Props) {
  const [expanded, setExpanded] = useState(false)

  const dateStr = new Date(card.published_at).toLocaleDateString('ko-KR', {
    month: 'short',
    day: 'numeric',
  })

  return (
    <article className="group bg-[#fbf9f3] border border-rule hover:border-ink/30 transition-colors">
      {/* 클릭 가능한 요약 영역 */}
      <button
        className="w-full text-left px-5 pt-4 pb-3.5 focus:outline-none focus-visible:ring-1 focus-visible:ring-ink"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        {/* 뱃지 행 */}
        <div className="flex items-center gap-3 mb-2.5 flex-wrap">
          <TypeBadge type="NEWS" />
          <span className="w-px h-3 bg-rule" aria-hidden />
          <CategoryBadge category={card.category} />
          <DifficultyBadge difficulty={card.difficulty} />
        </div>

        {/* 제목 */}
        <h2 className="font-serif text-[1.0625rem] font-bold text-ink leading-snug mb-1.5 tracking-[-0.01em]">
          {card.title}
        </h2>

        {/* 요약 2줄 clamp */}
        <p className="text-[0.8125rem] text-ink-soft line-clamp-2 leading-relaxed">{card.summary}</p>

        {/* 태그 + 날짜 */}
        <div className="flex items-center justify-between mt-3">
          <div className="flex gap-2.5 flex-wrap min-w-0">
            {card.tags.slice(0, 3).map((tag) => (
              <span key={tag.slug} className="font-mono text-[11px] text-ink-faint truncate">
                {tag.name}
              </span>
            ))}
          </div>
          <span className="font-mono text-[11px] text-ink-faint ml-2 flex-shrink-0">{dateStr}</span>
        </div>

        {/* 펼침 힌트 */}
        <div className="flex justify-center mt-2">
          <motion.span
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-ink-faint text-xs leading-none"
          >
            ▾
          </motion.span>
        </div>
      </button>

      {/* 펼침 콘텐츠 */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <NewsCardExpanded card={card} />
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  )
}
