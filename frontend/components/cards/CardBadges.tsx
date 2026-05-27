import { clsx } from 'clsx'
import type { Category, Difficulty, CardType } from '@/lib/types'

const CATEGORY_STYLES: Record<Category, string> = {
  CODING: 'bg-blue-100 text-blue-700',
  DESIGN: 'bg-violet-100 text-violet-700',
  GENERAL: 'bg-green-100 text-green-700',
}

const CATEGORY_LABEL: Record<Category, string> = {
  CODING: '프로그래밍',
  DESIGN: '디자인',
  GENERAL: '일반',
}

export function TypeBadge({ type }: { type: CardType }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium',
        type === 'NEWS'
          ? 'bg-orange-100 text-orange-700'
          : 'bg-indigo-100 text-indigo-700',
      )}
    >
      {type === 'NEWS' ? '📰 뉴스' : '⚙️ 기법'}
    </span>
  )
}

export function CategoryBadge({ category }: { category: Category }) {
  return (
    <span
      className={clsx(
        'px-2 py-0.5 rounded-full text-xs font-medium',
        CATEGORY_STYLES[category],
      )}
    >
      {CATEGORY_LABEL[category]}
    </span>
  )
}

export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  const filled = difficulty === 'BEGINNER' ? 1 : difficulty === 'INTERMEDIATE' ? 2 : 3
  return (
    <span className="text-xs tracking-tighter" aria-label={`난이도: ${difficulty}`}>
      {Array.from({ length: 3 }).map((_, i) => (
        <span key={i} className={i < filled ? 'text-amber-400' : 'text-gray-300'}>
          ★
        </span>
      ))}
    </span>
  )
}
