'use client'

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type AdminMetrics } from '@/lib/admin-api'
import { IS_DEMO } from '@/lib/demo'

function BarChart({ data }: { data: { date: string; cost_usd: number }[] }) {
  const max = Math.max(...data.map((d) => d.cost_usd), 0.001)
  return (
    <div className="flex items-end gap-1 h-32">
      {data.map((d) => {
        const pct = (d.cost_usd / max) * 100
        const label = new Date(d.date).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })
        return (
          <div key={d.date} className="flex-1 flex flex-col items-center gap-1 group">
            <span className="text-[10px] text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              ${d.cost_usd.toFixed(4)}
            </span>
            <div className="w-full relative" style={{ height: '96px' }}>
              <div
                className="absolute bottom-0 w-full bg-blue-400 rounded-t transition-all"
                style={{ height: `${Math.max(pct, 2)}%` }}
              />
            </div>
            <span className="text-[9px] text-gray-400 leading-none">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function CostsPage() {
  const user = useAuthStore((s) => s.user)
  const [data, setData] = useState<AdminMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user && !IS_DEMO) return
    adminApi.getMetrics().then(setData).catch(() => {}).finally(() => setLoading(false))
  }, [user])

  const budget = data?.monthly_budget_usd ?? 0
  const spent = data?.monthly_api_cost_usd ?? 0
  const pct = budget > 0 ? Math.min((spent / budget) * 100, 100) : 0

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-900">비용 현황</h1>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : !data ? null : (
        <>
          {/* 월 예산 게이지 */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="font-semibold text-gray-700">이번 달 지출</span>
              <span className="text-gray-500">
                <span className={pct >= 90 ? 'text-red-600 font-bold' : 'text-gray-800 font-semibold'}>
                  ${spent.toFixed(2)}
                </span>
                {' / '}${budget.toFixed(0)}
              </span>
            </div>
            <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-blue-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-gray-400">{pct.toFixed(1)}% 사용</p>
          </div>

          {/* 일별 비용 차트 */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            <p className="text-sm font-semibold text-gray-700">일별 API 비용 (최근 30일)</p>
            {data.daily_costs && data.daily_costs.length > 0 ? (
              <BarChart data={data.daily_costs} />
            ) : (
              <p className="text-xs text-gray-400 py-6 text-center">데이터가 없습니다.</p>
            )}
          </div>

          {/* 요약 카드 */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">일 평균 비용</p>
              <p className="text-xl font-bold text-gray-900">
                ${data.daily_costs && data.daily_costs.length > 0
                  ? (data.daily_costs.reduce((a, d) => a + d.cost_usd, 0) / data.daily_costs.length).toFixed(4)
                  : '0.0000'}
              </p>
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">남은 예산</p>
              <p className={`text-xl font-bold ${budget - spent < 5 ? 'text-red-600' : 'text-gray-900'}`}>
                ${Math.max(budget - spent, 0).toFixed(2)}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
