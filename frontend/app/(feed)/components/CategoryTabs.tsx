'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { clsx } from 'clsx'

const TABS = [
  { label: '전체', value: 'all' },
  { label: '프로그래밍', value: 'CODING' },
  { label: '디자인', value: 'DESIGN' },
  { label: '일반', value: 'GENERAL' },
] as const

interface Props {
  active: string
}

export default function CategoryTabs({ active }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()

  function handleClick(value: string) {
    const params = new URLSearchParams(searchParams.toString())
    if (value === 'all') params.delete('category')
    else params.set('category', value)
    params.delete('cursor')
    router.push(`/?${params}`)
  }

  return (
    <div className="flex gap-6 border-b border-ink overflow-x-auto">
      {TABS.map(({ label, value }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={clsx(
            'flex-shrink-0 pb-2.5 pt-1 text-[0.9375rem] font-serif font-bold border-b-2 -mb-px transition-colors',
            active === value
              ? 'border-accent text-ink'
              : 'border-transparent text-ink-faint hover:text-ink',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
