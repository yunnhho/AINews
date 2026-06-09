import { clsx } from 'clsx'
import type { Category, Difficulty, CardType } from '@/lib/types'

const CATEGORY_LABEL: Record<Category, string> = {
  CODING: '프로그래밍',
  DESIGN: '디자인',
  GENERAL: '일반',
}

const CATEGORY_DOT: Record<Category, string> = {
  CODING: 'bg-coding',
  DESIGN: 'bg-design',
  GENERAL: 'bg-general',
}

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  BEGINNER: '입문',
  INTERMEDIATE: '중급',
  ADVANCED: '심화',
}

export function TypeBadge({ type }: { type: CardType }) {
  const isNews = type === 'NEWS'
  return (
    <span
      className={clsx(
        'label-kicker inline-flex items-center gap-1.5',
        isNews ? 'text-accent' : 'text-ink',
      )}
    >
      <span
        className={clsx('inline-block w-[6px] h-[6px]', isNews ? 'bg-accent' : 'bg-ink')}
        aria-hidden
      />
      {isNews ? 'News' : 'Technique'}
    </span>
  )
}

export function CategoryBadge({ category }: { category: Category }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-ink-soft">
      <span
        className={clsx('inline-block w-1.5 h-1.5 rounded-full', CATEGORY_DOT[category])}
        aria-hidden
      />
      {CATEGORY_LABEL[category]}
    </span>
  )
}

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  const filled = difficulty === 'BEGINNER' ? 1 : difficulty === 'INTERMEDIATE' ? 2 : 3
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] text-ink-faint"
      aria-label={`난이도: ${DIFFICULTY_LABEL[difficulty]}`}
    >
      <span className="flex items-center gap-[3px]">
        {Array.from({ length: 3 }).map((_, i) => (
          <span
            key={i}
            className={clsx('inline-block w-3 h-[2px]', i < filled ? 'bg-ink' : 'bg-rule')}
          />
        ))}
      </span>
      {DIFFICULTY_LABEL[difficulty]}
    </span>
  )
}
