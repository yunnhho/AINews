import Link from 'next/link'
import HeaderAuth from './HeaderAuth'

export default function Header() {
  return (
    <header className="fixed top-0 inset-x-0 h-14 bg-white border-b border-gray-200 z-40 flex items-center px-4 gap-4">
      <Link href="/" className="font-bold text-lg tracking-tight text-gray-900">
        AI Pulse
      </Link>
      <span className="text-xs text-gray-400 hidden sm:block">AI/LLM 뉴스 카드</span>
      <div className="ml-auto">
        <HeaderAuth />
      </div>
    </header>
  )
}
