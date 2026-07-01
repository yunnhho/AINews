'use client'

import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type BatchLog } from '@/lib/admin-api'
import { IS_DEMO } from '@/lib/demo'

const STATUS_STYLE: Record<BatchLog['status'], string> = {
  COMPLETED: 'bg-green-100 text-green-700',
  PARTIAL_FAILURE: 'bg-yellow-100 text-yellow-700',
  FAILED: 'bg-red-100 text-red-700',
  RUNNING: 'bg-blue-100 text-blue-700',
  SCHEDULED: 'bg-gray-100 text-gray-600',
}

const STATUS_LABEL: Record<BatchLog['status'], string> = {
  COMPLETED: '완료',
  PARTIAL_FAILURE: '부분 실패',
  FAILED: '실패',
  RUNNING: '실행 중',
  SCHEDULED: '예정',
}

export default function BatchesPage() {
  const user = useAuthStore((s) => s.user)
  const [batches, setBatches] = useState<BatchLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user && !IS_DEMO) return
    adminApi.getBatches().then((r) => setBatches(r.items)).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">배치 이력</h1>
      {loading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 bg-gray-200 rounded-lg animate-pulse" />)}</div>
      ) : batches.length === 0 ? (
        <p className="text-sm text-gray-400 py-10 text-center">배치 기록이 없습니다.</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {['배치 ID', '예정 시각', '상태', '발행', '중복 제거', '비용'].map((h) => (
                  <th key={h} className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {batches.map((b) => {
                const published = b.published_by_type
                  ? Object.values(b.published_by_type).reduce((a, c) => a + c, 0)
                  : 0
                return (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-600 truncate max-w-[160px]">{b.batch_id}</td>
                    <td className="px-4 py-2.5 text-xs text-gray-600 whitespace-nowrap">
                      {new Date(b.scheduled_at).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium', STATUS_STYLE[b.status])}>
                        {STATUS_LABEL[b.status]}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-gray-700">{published}장</td>
                    <td className="px-4 py-2.5 text-xs text-gray-700">{b.deduplicated_count}건</td>
                    <td className="px-4 py-2.5 text-xs text-gray-700">${Number(b.api_cost_usd).toFixed(4)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
