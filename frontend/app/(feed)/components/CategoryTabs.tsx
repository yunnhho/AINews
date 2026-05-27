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
    <div className="flex border-b border-gray-200 bg-white overflow-x-auto">
      {TABS.map(({ label, value }) => (
        <button
          key={value}
          onClick={() => handleClick(value)}
          className={clsx(
            'flex-shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
            active === value
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
          )}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
