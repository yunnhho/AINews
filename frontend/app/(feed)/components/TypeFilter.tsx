'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { clsx } from 'clsx'

const TYPES = [
  { label: '전체', value: 'all', icon: null },
  { label: '뉴스', value: 'NEWS', icon: '📰' },
  { label: '기법', value: 'TECHNIQUE', icon: '⚙️' },
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
    <div className="flex items-center gap-1 px-4 py-2 bg-white border-b border-gray-100">
      {TYPES.map(({ label, value, icon }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={clsx(
            'flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
            active === value
              ? 'bg-gray-900 text-white'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
          )}
        >
          {icon && <span>{icon}</span>}
          {label}
        </button>
      ))}
    </div>
  )
}
