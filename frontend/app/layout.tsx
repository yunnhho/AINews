import type { Metadata } from 'next'
import './globals.css'
import Header from '@/components/Header'

export const metadata: Metadata = {
  title: 'AI Pulse — AI·LLM 뉴스 카드',
  description: 'AI와 LLM 분야의 최신 뉴스·기법을 카드 형식으로 큐레이션합니다.',
  manifest: '/manifest.json',
  openGraph: { siteName: 'AI Pulse', type: 'website' },
  other: { 'theme-color': '#1C1A17' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        {/* Pretendard: 한국 웹·IT 독자에게 가장 익숙하고 가독성 높은 본문/제목 폰트 */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Header />
        <main className="pt-[var(--header-height)]">{children}</main>
      </body>
    </html>
  )
}
