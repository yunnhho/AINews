'use client'

import type { NewsCard } from '@/lib/types'
import CardActions from './CardActions'

interface Props {
  card: NewsCard
}

export default function NewsCardExpanded({ card }: Props) {
  return (
    <div className="px-4 pb-4 pt-3 border-t border-gray-100 space-y-4">
      {/* 핵심 포인트 */}
      {card.key_points.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            핵심 포인트
          </h3>
          <ul className="space-y-1.5">
            {card.key_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-1 flex-shrink-0 w-4 h-4 rounded-full bg-blue-100 text-blue-600 text-[10px] flex items-center justify-center font-bold">
                  {i + 1}
                </span>
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 소스 + 원문 링크 */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <span className="text-xs text-gray-400">{card.source_name}</span>
        <a
          href={card.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
        >
          원문 보기 →
        </a>
      </div>

      {/* 좋아요 / 북마크 / 공유 */}
      <CardActions card={card} />
    </div>
  )
}
