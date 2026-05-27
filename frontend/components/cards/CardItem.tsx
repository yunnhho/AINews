'use client'

import type { Card } from '@/lib/types'
import NewsCard from './NewsCard'
import TechniqueCard from './TechniqueCard'

export default function CardItem({ card }: { card: Card }) {
  if (card.card_type === 'NEWS') return <NewsCard card={card} />
  return <TechniqueCard card={card} />
}
