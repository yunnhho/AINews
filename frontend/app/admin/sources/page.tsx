'use client'

import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type SourceHealth } from '@/lib/admin-api'
import { IS_DEMO } from '@/lib/demo'

export default function SourcesPage() {
  const user = useAuthStore((s) => s.user)
  const [sources, setSources] = useState<SourceHealth[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<number | null>(null)

  useEffect(() => {
    if (!user && !IS_DEMO) return
    adminApi.getSourceHealth().then((r) => setSources(r.items)).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  async function handleToggle(src: SourceHealth) {
    if (IS_DEMO || !user || toggling !== null) return  // 데모: 쓰기 비활성
    setToggling(src.source_id)
    try {
      await adminApi.toggleSource(src.source_id, !src.enabled)
      setSources((prev) =>
        prev.map((s) => s.source_id === src.source_id ? { ...s, enabled: !s.enabled } : s)
      )
    } catch { /* silently fail */ }
    setToggling(null)
  }

  const grouped = sources.reduce<Record<string, SourceHealth[]>>((acc, s) => {
    ;(acc[s.source_group] ??= []).push(s)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">소스 관리</h1>
      {loading ? (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-12 bg-gray-200 rounded-lg animate-pulse" />)}</div>
      ) : (
        Object.entries(grouped).map(([group, items]) => (
          <div key={group}>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{group}</h2>
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              {items.map((src, i) => (
                <div
                  key={src.source_id}
                  className={clsx('flex items-center px-4 py-3 gap-3', i !== 0 && 'border-t border-gray-100')}
                >
                  {/* 상태 불 */}
                  <span
                    className={clsx(
                      'w-2 h-2 rounded-full flex-shrink-0',
                      !src.enabled ? 'bg-gray-300'
                        : src.consecutive_failures >= 3 ? 'bg-red-500'
                        : src.consecutive_failures > 0 ? 'bg-yellow-400'
                        : 'bg-green-400',
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800">{src.source_name}</p>
                    {src.consecutive_failures > 0 && (
                      <p className="text-xs text-red-500">연속 실패 {src.consecutive_failures}회</p>
                    )}
                    {src.last_success_at && src.consecutive_failures === 0 && (
                      <p className="text-xs text-gray-400">
                        마지막 성공: {new Date(src.last_success_at).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </p>
                    )}
                  </div>
                  {/* 토글 */}
                  <button
                    onClick={() => handleToggle(src)}
                    disabled={IS_DEMO || toggling === src.source_id}
                    className={clsx(
                      'relative inline-flex h-5 w-9 flex-shrink-0 rounded-full transition-colors duration-200',
                      src.enabled ? 'bg-blue-500' : 'bg-gray-300',
                      (toggling === src.source_id || IS_DEMO) && 'opacity-50 cursor-not-allowed',
                    )}
                    aria-label={src.enabled ? '비활성화' : '활성화'}
                  >
                    <span
                      className={clsx(
                        'inline-block h-4 w-4 rounded-full bg-white shadow translate-y-0.5 transition-transform duration-200',
                        src.enabled ? 'translate-x-4' : 'translate-x-0.5',
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
