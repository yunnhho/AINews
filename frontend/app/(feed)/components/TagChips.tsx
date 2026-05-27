'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { clsx } from 'clsx'
import type { Tag } from '@/lib/types'

interface Props {
  tags: Tag[]
  activeSlugs: string[]
}

export default function TagChips({ tags, activeSlugs }: Props) {
  const router = useRouter()
  const searchParams = useSearchParams()

  if (tags.length === 0) return null

  function handleClick(slug: string) {
    const params = new URLSearchParams(searchParams.toString())
    const current = params.getAll('tags')
    if (current.includes(slug)) {
      params.delete('tags')
      current.filter((s) => s !== slug).forEach((s) => params.append('tags', s))
    } else {
      params.append('tags', slug)
    }
    params.delete('cursor')
    router.push(`/?${params}`)
  }

  return (
    <div className="flex items-center gap-1.5 px-4 py-2 bg-white border-b border-gray-100 overflow-x-auto">
      {tags.map((tag) => {
        const isActive = activeSlugs.includes(tag.slug)
        return (
          <button
            key={tag.slug}
            onClick={() => handleClick(tag.slug)}
            className={clsx(
              'flex-shrink-0 px-2.5 py-1 rounded-full text-xs transition-colors',
              isActive
                ? 'bg-blue-100 text-blue-700 font-medium'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200',
            )}
          >
            #{tag.name}
          </button>
        )
      })}
    </div>
  )
}
