'use client'

import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'
import { likeCard, unlikeCard, bookmarkCard, unbookmarkCard } from '@/lib/api'
import type { Card } from '@/lib/types'
import AuthModal from '@/components/AuthModal'

declare global {
  interface Window {
    Kakao?: {
      isInitialized: () => boolean
      init: (key: string) => void
      Share: {
        sendDefault: (opts: object) => void
      }
    }
  }
}

interface Props {
  card: Card
}

export default function CardActions({ card }: Props) {
  const { token } = useAuthStore()
  const [isLiked, setIsLiked] = useState(card.is_liked)
  const [likeCount, setLikeCount] = useState(card.like_count)
  const [isBookmarked, setIsBookmarked] = useState(card.is_bookmarked)
  const [bookmarkCount, setBookmarkCount] = useState(card.bookmark_count)
  const [showAuth, setShowAuth] = useState(false)

  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_KAKAO_JS_KEY
    if (!key) return
    if (document.getElementById('kakao-sdk')) return
    const script = document.createElement('script')
    script.id = 'kakao-sdk'
    script.src = 'https://t1.kakaocdn.net/kakao_js_sdk/2.7.2/kakao.min.js'
    script.crossOrigin = 'anonymous'
    script.onload = () => {
      if (window.Kakao && !window.Kakao.isInitialized()) window.Kakao.init(key)
    }
    document.head.appendChild(script)
  }, [])

  async function toggleLike() {
    if (!token) { setShowAuth(true); return }
    const snapshot = { isLiked, likeCount }
    setIsLiked(!isLiked)
    setLikeCount(isLiked ? likeCount - 1 : likeCount + 1)
    try {
      if (isLiked) await unlikeCard(card.id, token)
      else await likeCard(card.id, token)
    } catch {
      setIsLiked(snapshot.isLiked)
      setLikeCount(snapshot.likeCount)
    }
  }

  async function toggleBookmark() {
    if (!token) { setShowAuth(true); return }
    const snapshot = { isBookmarked, bookmarkCount }
    setIsBookmarked(!isBookmarked)
    setBookmarkCount(isBookmarked ? bookmarkCount - 1 : bookmarkCount + 1)
    try {
      if (isBookmarked) await unbookmarkCard(card.id, token)
      else await bookmarkCard(card.id, token)
    } catch {
      setIsBookmarked(snapshot.isBookmarked)
      setBookmarkCount(snapshot.bookmarkCount)
    }
  }

  function handleShare() {
    const url = `${typeof window !== 'undefined' ? window.location.origin : 'https://aipulse.kr'}/cards/${card.id}`
    if (typeof navigator.share === 'function') {
      navigator.share({ title: card.title, url }).catch(() => {})
    } else {
      navigator.clipboard.writeText(url).catch(() => {})
    }
  }

  function handleKakaoShare() {
    const url = `${typeof window !== 'undefined' ? window.location.origin : 'https://aipulse.kr'}/cards/${card.id}`
    if (!window.Kakao?.Share) return
    window.Kakao.Share.sendDefault({
      objectType: 'feed',
      content: {
        title: card.title,
        description: (card as { summary?: string }).summary ?? '',
        link: { mobileWebUrl: url, webUrl: url },
      },
    })
  }

  return (
    <>
      <div className="flex items-center gap-4">
        <button
          onClick={toggleLike}
          className={clsx(
            'flex items-center gap-1 text-xs transition-colors',
            isLiked ? 'text-red-500' : 'text-gray-400 hover:text-red-400',
          )}
          aria-label={isLiked ? '좋아요 취소' : '좋아요'}
        >
          {isLiked ? '❤️' : '🤍'} {likeCount}
        </button>
        <button
          onClick={toggleBookmark}
          className={clsx(
            'flex items-center gap-1 text-xs transition-colors',
            isBookmarked ? 'text-blue-500' : 'text-gray-400 hover:text-blue-400',
          )}
          aria-label={isBookmarked ? '북마크 취소' : '북마크'}
        >
          {isBookmarked ? '🔖' : '📄'} {bookmarkCount}
        </button>
        <button
          onClick={handleShare}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="공유"
        >
          🔗
        </button>
        {process.env.NEXT_PUBLIC_KAKAO_JS_KEY && (
          <button
            onClick={handleKakaoShare}
            className="text-xs text-gray-400 hover:text-yellow-500 transition-colors"
            aria-label="카카오톡 공유"
          >
            💬
          </button>
        )}
      </div>
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} />
    </>
  )
}
