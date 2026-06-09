'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { clsx } from 'clsx'

const TYPES = [
  { label: '전체', value: 'all' },
  { label: '뉴스', value: 'NEWS' },
  { label: '기법', value: 'TECHNIQUE' },
] as const

interface Props {
  active: string
}

export default function TypeFilter({ active }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()

  function handleClick(value: string) {
    const params = new URLSearchParams(searchParams.toString())
    if (value === 'all') params.delete('card_type')
    else params.set('card_type', value)
    params.delete('cursor')
    router.push(`/?${params}`)
  }

  return (
    <div className="flex items-center gap-2 px-1 py-2.5">
      {TYPES.map(({ label, value }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={clsx(
            'label-kicker px-2.5 py-1 border transition-colors',
            active === value
              ? 'bg-ink text-paper border-ink'
              : 'border-rule text-ink-soft hover:border-ink',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
