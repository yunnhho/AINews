export type CardType = 'NEWS' | 'TECHNIQUE'
export type Category = 'CODING' | 'DESIGN' | 'GENERAL'
export type Difficulty = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'
export type SourceGroup = 'NEWS_RSS' | 'GITHUB' | 'ENG_BLOG' | 'NEWSLETTER'

export interface Tag {
  name: string
  slug: string
}

interface BaseCard {
  id: number
  card_type: CardType
  category: Category
  difficulty: Difficulty
  title: string
  summary: string
  source_url: string
  source_name: string
  source_group: SourceGroup
  tags: Tag[]
  thumbnail_url: string | null
  like_count: number
  bookmark_count: number
  published_at: string
  is_liked: boolean
  is_bookmarked: boolean
}

export interface NewsCard extends BaseCard {
  card_type: 'NEWS'
  key_points: string[]
}

export interface TechniqueCard extends BaseCard {
  card_type: 'TECHNIQUE'
  problem: string
  idea: string
  code_snippet: string | null
  caveats: string[]
  prerequisites: string | null
}

export type Card = NewsCard | TechniqueCard

export interface FeedResponse {
  items: Card[]
  next_cursor: string | null
  has_more: boolean
}

export interface FeedParams {
  category?: string
  card_type?: string
  tags?: string[]
  difficulty?: string
  cursor?: string
  limit?: number
}
