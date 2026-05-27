import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { getCard } from '@/lib/api'
import CardItem from '@/components/cards/CardItem'

type Props = { params: Promise<{ id: string }> }

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://aipulse.kr'

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params
  const card = await getCard(Number(id)).catch(() => null)
  if (!card) return { title: '카드를 찾을 수 없습니다 — AI Pulse' }

  return {
    title: `${card.title} — AI Pulse`,
    description: card.summary,
    openGraph: {
      title: card.title,
      description: card.summary,
      type: 'article',
      publishedTime: card.published_at,
      siteName: 'AI Pulse',
    },
    twitter: { card: 'summary_large_image', title: card.title, description: card.summary },
  }
}

export default async function CardDetailPage({ params }: Props) {
  const { id } = await params
  const card = await getCard(Number(id)).catch(() => null)
  if (!card) notFound()

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: card.title,
    description: card.summary,
    datePublished: card.published_at,
    publisher: { '@type': 'Organization', name: 'AI Pulse', url: BASE_URL },
    url: `${BASE_URL}/cards/${card.id}`,
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <CardItem card={card} />
    </div>
  )
}
