'use client'

import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'
import { getCard, likeCard, unlikeCard, bookmarkCard, unbookmarkCard, ApiError } from '@/lib/api'
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

  // SSR 데이터는 토큰이 없어 is_liked/is_bookmarked가 false다.
  // 로그인 상태면 서버의 실제 좋아요/북마크 상태로 동기화한다.
  // (CardActions는 카드 확장 시 또는 상세 페이지에서만 마운트되므로 요청 비용이 작다.)
  useEffect(() => {
    if (!token) return
    let cancelled = false
    getCard(card.id, token)
      .then((fresh) => {
        if (cancelled) return
        setIsLiked(fresh.is_liked)
        setLikeCount(fresh.like_count)
        setIsBookmarked(fresh.is_bookmarked)
        setBookmarkCount(fresh.bookmark_count)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [token, card.id])

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
    } catch (e) {
      setIsLiked(snapshot.isLiked)
      setLikeCount(snapshot.likeCount)
      // 토큰 만료(401)면 스토어가 비워졌으므로 재로그인을 유도한다.
      if (e instanceof ApiError && e.status === 401) setShowAuth(true)
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
    } catch (e) {
      setIsBookmarked(snapshot.isBookmarked)
      setBookmarkCount(snapshot.bookmarkCount)
      // 토큰 만료(401)면 스토어가 비워졌으므로 재로그인을 유도한다.
      if (e instanceof ApiError && e.status === 401) setShowAuth(true)
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
      <div className="flex items-center gap-5">
        <button
          onClick={toggleLike}
          className={clsx(
            'flex items-center gap-1.5 transition-colors',
            isLiked ? 'text-accent' : 'text-ink-faint hover:text-accent',
          )}
          aria-label={isLiked ? '좋아요 취소' : '좋아요'}
        >
          <span className="text-sm leading-none">{isLiked ? '♥' : '♡'}</span>
          <span className="font-mono text-[11px]">{likeCount}</span>
        </button>
        <button
          onClick={toggleBookmark}
          className={clsx(
            'flex items-center gap-1.5 transition-colors',
            isBookmarked ? 'text-ink' : 'text-ink-faint hover:text-ink',
          )}
          aria-label={isBookmarked ? '북마크 취소' : '북마크'}
        >
          <span className="text-[11px] leading-none">{isBookmarked ? '■' : '□'}</span>
          <span className="font-mono text-[11px]">북마크 {bookmarkCount}</span>
        </button>
        <button
          onClick={handleShare}
          className="label-kicker text-ink-faint hover:text-ink transition-colors"
          aria-label="공유"
        >
          공유
        </button>
        {process.env.NEXT_PUBLIC_KAKAO_JS_KEY && (
          <button
            onClick={handleKakaoShare}
            className="label-kicker text-ink-faint hover:text-accent transition-colors"
            aria-label="카카오톡 공유"
          >
            카카오
          </button>
        )}
      </div>
      <AuthModal open={showAuth} onClose={() => setShowAuth(false)} />
    </>
  )
}
