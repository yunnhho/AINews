'use client'

import type { NewsCard } from '@/lib/types'
import CardActions from './CardActions'

interface Props {
  card: NewsCard
}

export default function NewsCardExpanded({ card }: Props) {
  return (
    <div className="px-5 pb-5 pt-4 rule-t space-y-5 bg-paper/40">
      {/* 핵심 포인트 */}
      {card.key_points.length > 0 && (
        <div>
          <h3 className="label-kicker text-accent mb-2.5">Key Points · 핵심 포인트</h3>
          <ul className="space-y-2">
            {card.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-3 text-[0.875rem] text-ink leading-relaxed">
                <span className="mt-0.5 flex-shrink-0 font-serif font-bold text-ink-faint tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 소스 + 원문 링크 */}
      <div className="flex items-center justify-between pt-3 rule-t">
        <span className="font-mono text-[11px] text-ink-faint">{card.source_name}</span>
        <a
          href={card.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="label-kicker text-accent hover:text-accent-ink"
        >
          원문 보기 →
        </a>
      </div>

      {/* 좋아요 / 북마크 / 공유 */}
      <CardActions card={card} />
    </div>
  )
}
