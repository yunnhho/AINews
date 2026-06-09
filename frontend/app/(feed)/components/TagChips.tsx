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
    <div className="flex items-center gap-3 py-2.5 overflow-x-auto">
      {tags.map((tag) => {
        const isActive = activeSlugs.includes(tag.slug)
        return (
          <button
            key={tag.slug}
            onClick={() => handleClick(tag.slug)}
            className={clsx(
              'flex-shrink-0 font-mono text-[11px] whitespace-nowrap transition-colors',
              isActive
                ? 'text-accent underline underline-offset-4 decoration-accent'
                : 'text-ink-faint hover:text-ink',
            )}
          >
            {tag.name}
          </button>
        )
      })}
    </div>
  )
}
