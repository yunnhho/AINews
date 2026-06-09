import Link from 'next/link'
import HeaderAuth from './HeaderAuth'

const NAV = [
  { href: '/recommended', label: '추천' },
  { href: '/search', label: '검색' },
  { href: '/bookmarks', label: '북마크' },
]

export default function Header() {
  return (
    <header className="fixed top-0 inset-x-0 z-40 bg-paper/95 backdrop-blur-sm border-b border-ink">
      <div className="h-[59px] flex items-center px-4 sm:px-6 gap-5 max-w-3xl mx-auto">
        <Link href="/" className="flex items-baseline gap-2 group">
          <span className="font-serif text-xl font-extrabold tracking-[-0.02em] text-ink">
            AI&nbsp;Pulse
          </span>
          <span className="hidden sm:inline label-kicker text-accent">매일의 AI 큐레이션</span>
        </Link>

        <nav className="ml-auto flex items-center gap-4 sm:gap-5">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="label-kicker text-ink-soft hover:text-ink transition-colors"
            >
              {n.label}
            </Link>
          ))}
          <span className="w-px h-4 bg-rule" aria-hidden />
          <HeaderAuth />
        </nav>
      </div>
    </header>
  )
}
