'use client'

import type { TechniqueCard } from '@/lib/types'
import CardActions from './CardActions'
import CodeBlock from './CodeBlock'

interface Props {
  card: TechniqueCard
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
        {title}
      </h3>
      {children}
    </div>
  )
}

export default function TechniqueCardExpanded({ card }: Props) {
  return (
    <div className="px-4 pb-4 pt-3 border-t border-gray-100 space-y-4">
      {/* ① 문제 */}
      <Section title="문제">
        <p className="text-sm text-gray-700 leading-relaxed">{card.problem}</p>
      </Section>

      {/* ② 핵심 아이디어 */}
      <Section title="핵심 아이디어">
        <p className="text-sm text-gray-700 leading-relaxed">{card.idea}</p>
      </Section>

      {/* ③ 코드 (있을 때만) */}
      {card.code_snippet && (
        <Section title="코드">
          <CodeBlock code={card.code_snippet} />
        </Section>
      )}

      {/* ④ 주의사항 */}
      {card.caveats.length > 0 && (
        <Section title="주의사항">
          <ul className="space-y-1">
            {card.caveats.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="mt-1 flex-shrink-0 text-amber-500">⚠</span>
                {c}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 선행지식 */}
      {card.prerequisites && (
        <div className="flex items-center gap-1.5 text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
          <span>📚</span>
          <span>
            <span className="font-medium">선행지식:</span> {card.prerequisites}
          </span>
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
