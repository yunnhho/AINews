'use client'

import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type TranslationItem } from '@/lib/admin-api'

export default function TranslationPage() {
  const { token } = useAuthStore()
  const [items, setItems] = useState<TranslationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<number | null>(null)

  useEffect(() => {
    if (!token) return
    adminApi.getTranslationQueue(token).then((r) => setItems(r.items)).catch(() => {}).finally(() => setLoading(false))
  }, [token])

  async function handleReview(logId: number, action: 'approve' | 'reject') {
    if (!token) return
    try {
      await adminApi.reviewTranslation(logId, action, token)
      setItems((prev) =>
        action === 'reject'
          ? prev.filter((i) => i.id !== logId)
          : prev.map((i) => (i.id === logId ? { ...i, passed: true } : i)),
      )
      if (expanded === logId) setExpanded(null)
    } catch {
      // 실패 시 무시 (UI 유지)
    }
  }

  const failed = items.filter((i) => !i.passed)
  const passed = items.filter((i) => i.passed)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">번역 큐</h1>
        <div className="flex gap-3 text-xs text-gray-500">
          <span>✅ 통과 {passed.length}건</span>
          <span>❌ 실패 {failed.length}건</span>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />)}</div>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-400 py-10 text-center">번역 기록이 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.id}
              className={clsx(
                'bg-white border rounded-xl overflow-hidden',
                item.passed ? 'border-green-200' : 'border-red-200',
              )}
            >
              <button
                className="w-full text-left px-4 py-3 flex items-center gap-3"
                onClick={() => setExpanded(expanded === item.id ? null : item.id)}
              >
                <span>{item.passed ? '✅' : '❌'}</span>
                <span className="flex-1 text-sm font-medium text-gray-700 truncate">
                  카드 #{item.card_id}
                </span>
                {item.similarity_score != null && (
                  <span className={clsx('text-xs font-mono', item.passed ? 'text-green-600' : 'text-red-500')}>
                    sim={item.similarity_score.toFixed(3)}
                  </span>
                )}
                <span className="text-xs text-gray-400">
                  {new Date(item.created_at).toLocaleDateString('ko-KR')}
                </span>
              </button>
              {expanded === item.id && (
                <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-3 text-xs">
                  <div>
                    <p className="font-semibold text-gray-500 mb-1">원문</p>
                    <p className="text-gray-700 bg-gray-50 rounded p-2 line-clamp-3">{item.original_text}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-500 mb-1">한국어 번역</p>
                    <p className="text-gray-700 bg-gray-50 rounded p-2">{item.translated_text}</p>
                  </div>
                  {item.back_translated_text && (
                    <div>
                      <p className="font-semibold text-gray-500 mb-1">역번역</p>
                      <p className="text-gray-700 bg-gray-50 rounded p-2">{item.back_translated_text}</p>
                    </div>
                  )}
                  {!item.passed && (
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleReview(item.id, 'approve')}
                        className="px-3 py-1.5 text-xs font-medium bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                      >
                        ✅ 통과
                      </button>
                      <button
                        onClick={() => handleReview(item.id, 'reject')}
                        className="px-3 py-1.5 text-xs font-medium bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                      >
                        🗑️ 삭제
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
