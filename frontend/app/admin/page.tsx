'use client'

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type AdminMetrics } from '@/lib/admin-api'

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function AdminDashboard() {
  const { token } = useAuthStore()
  const [data, setData] = useState<AdminMetrics | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!token) return
    adminApi.getMetrics(token).then(setData).catch(() => setError(true))
  }, [token])

  if (error) {
    return (
      <div className="text-center py-20 text-gray-400">
        <p className="text-4xl mb-3">🔧</p>
        <p className="text-sm">관리자 API를 불러올 수 없습니다.</p>
        <p className="text-xs mt-1 text-gray-300">백엔드 서버 상태를 확인하세요.</p>
      </div>
    )
  }

  if (!data) {
    return <div className="animate-pulse space-y-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-20 bg-gray-200 rounded-xl" />
      ))}
    </div>
  }

  const totalToday = Object.values(data.today_published).reduce((a, b) => a + b, 0)
  const alertCount = data.alert_sources.length

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">대시보드</h1>

      {/* 주요 지표 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <MetricCard
          label="오늘 발행"
          value={`${totalToday}장`}
          sub={`뉴스 ${data.today_published.NEWS ?? 0} · 기법 ${data.today_published.TECHNIQUE ?? 0}`}
        />
        <MetricCard
          label="배치 성공률 (7일)"
          value={`${(data.batch_success_rate_7d * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="번역 검증 통과율"
          value={`${(data.translation_pass_rate * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="이번 달 API 비용"
          value={`$${data.monthly_api_cost_usd.toFixed(2)}`}
          sub={`예산 $${data.monthly_budget_usd.toFixed(0)}`}
        />
        <MetricCard
          label="소스 이상 경보"
          value={`${alertCount}건`}
          sub={alertCount > 0 ? '즉시 확인 필요' : '정상'}
        />
      </div>

      {/* 소스 이상 경보 목록 */}
      {alertCount > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">⚠️ 이상 소스</h2>
          <div className="space-y-2">
            {data.alert_sources.map((src) => (
              <div
                key={src.source_id}
                className="bg-red-50 border border-red-200 rounded-lg px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-red-700">{src.source_name}</span>
                  <span className="text-xs text-red-500">연속 실패 {src.consecutive_failures}회</span>
                </div>
                {src.last_error_log && (
                  <p className="text-xs text-red-400 mt-0.5 truncate">{src.last_error_log}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
