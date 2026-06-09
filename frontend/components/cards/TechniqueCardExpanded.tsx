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
      <h3 className="label-kicker text-accent mb-2">{title}</h3>
      {children}
    </div>
  )
}

export default function TechniqueCardExpanded({ card }: Props) {
  return (
    <div className="px-5 pb-5 pt-4 rule-t space-y-5 bg-paper/40">
      {/* ① 문제 */}
      <Section title="Problem · 문제">
        <p className="text-[0.875rem] text-ink leading-relaxed">{card.problem}</p>
      </Section>

      {/* ② 핵심 아이디어 */}
      <Section title="Idea · 핵심 아이디어">
        <p className="text-[0.875rem] text-ink leading-relaxed">{card.idea}</p>
      </Section>

      {/* ③ 코드 (있을 때만) */}
      {card.code_snippet && (
        <Section title="Code · 코드">
          <CodeBlock code={card.code_snippet} />
        </Section>
      )}

      {/* ④ 주의사항 */}
      {card.caveats.length > 0 && (
        <Section title="Caveats · 주의사항">
          <ul className="space-y-1.5">
            {card.caveats.map((c, i) => (
              <li key={i} className="flex items-start gap-2.5 text-[0.875rem] text-ink leading-relaxed">
                <span className="mt-2 flex-shrink-0 w-1.5 h-1.5 bg-accent" aria-hidden />
                {c}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* 선행지식 */}
      {card.prerequisites && (
        <p className="text-[0.8125rem] text-ink-soft border-l-2 border-rule pl-3 py-0.5">
          <span className="label-kicker text-ink-faint mr-1.5">선행지식</span>
          {card.prerequisites}
        </p>
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
