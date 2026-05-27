import type { MetadataRoute } from 'next'
import { getCards } from '@/lib/api'

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://aipulse.kr'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const data = await getCards({ limit: 1000 }).catch(() => ({ items: [] as never[] }))

  const cardEntries: MetadataRoute.Sitemap = data.items.map((card) => ({
    url: `${BASE_URL}/cards/${card.id}`,
    lastModified: new Date(card.published_at),
    changeFrequency: 'weekly',
    priority: 0.8,
  }))

  return [
    { url: BASE_URL, lastModified: new Date(), changeFrequency: 'hourly', priority: 1 },
    { url: `${BASE_URL}/?card_type=NEWS`, changeFrequency: 'hourly', priority: 0.9 },
    { url: `${BASE_URL}/?card_type=TECHNIQUE`, changeFrequency: 'daily', priority: 0.9 },
    ...cardEntries,
  ]
}
