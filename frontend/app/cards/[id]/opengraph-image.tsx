import { ImageResponse } from 'next/og'
import { getCard } from '@/lib/api'

export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

const CATEGORY_COLOR: Record<string, string> = {
  CODING: '#3B82F6',
  DESIGN: '#8B5CF6',
  GENERAL: '#22C55E',
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const card = await getCard(Number(id)).catch(() => null)

  const title = card?.title ?? 'AI Pulse'
  const summary = (card?.summary ?? 'AI/LLM 뉴스 카드 플랫폼').slice(0, 100)
  const type = card?.card_type
  const category = card?.category ?? 'GENERAL'
  const accentColor = CATEGORY_COLOR[category] ?? '#3B82F6'

  return new ImageResponse(
    (
      <div
        style={{
          background: '#0f172a',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          padding: '64px',
          fontFamily: 'sans-serif',
          position: 'relative',
        }}
      >
        {/* 컬러 액센트 바 */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '6px',
            background: accentColor,
          }}
        />

        {/* 헤더: 로고 + 타입 뱃지 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '40px' }}>
          <span style={{ color: '#fff', fontSize: '28px', fontWeight: '700' }}>AI Pulse</span>
          {type && (
            <span
              style={{
                background: type === 'NEWS' ? '#ea580c' : '#4f46e5',
                color: '#fff',
                padding: '4px 14px',
                borderRadius: '999px',
                fontSize: '16px',
                fontWeight: '600',
              }}
            >
              {type === 'NEWS' ? '📰 뉴스' : '⚙️ 기법'}
            </span>
          )}
        </div>

        {/* 제목 */}
        <div
          style={{
            color: '#f1f5f9',
            fontSize: '52px',
            fontWeight: '800',
            lineHeight: '1.2',
            marginBottom: '28px',
            flex: 1,
          }}
        >
          {title}
        </div>

        {/* 요약 */}
        <div style={{ color: '#94a3b8', fontSize: '24px', lineHeight: '1.5' }}>{summary}</div>
      </div>
    ),
    size,
  )
}
