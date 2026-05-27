import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Pulse — AI/LLM 뉴스 카드',
  description: 'AI와 LLM 분야의 최신 뉴스·기법을 카드 형식으로 제공합니다.',
  manifest: '/manifest.json',
  openGraph: { siteName: 'AI Pulse', type: 'website' },
  other: { 'theme-color': '#3B82F6' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Header />
        <main className="pt-[var(--header-height)]">{children}</main>
      </body>
    </html>
  )
}
