import { Text, View } from 'react-native'
import type { CardType, Category, Difficulty } from '@/lib/types'

const TYPE_LABEL: Record<CardType, string> = {
  NEWS: '📰 뉴스',
  TECHNIQUE: '⚙️ 기법',
}

const CATEGORY_BG: Record<Category, string> = {
  CODING: 'bg-blue-100',
  DESIGN: 'bg-purple-100',
  GENERAL: 'bg-green-100',
}

const CATEGORY_TEXT: Record<Category, string> = {
  CODING: 'text-blue-700',
  DESIGN: 'text-purple-700',
  GENERAL: 'text-green-700',
}

const CATEGORY_LABEL: Record<Category, string> = {
  CODING: '프로그래밍',
  DESIGN: '디자인',
  GENERAL: '일반',
}

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  BEGINNER: '초급',
  INTERMEDIATE: '중급',
  ADVANCED: '고급',
}

interface Props {
  cardType: CardType
  category: Category
  difficulty: Difficulty
}

export function CardBadges({ cardType, category, difficulty }: Props) {
  return (
    <View className="flex-row flex-wrap gap-1.5">
      <View className="bg-gray-100 rounded-full px-2.5 py-0.5">
        <Text className="text-xs text-gray-600">{TYPE_LABEL[cardType]}</Text>
      </View>
      <View className={`${CATEGORY_BG[category]} rounded-full px-2.5 py-0.5`}>
        <Text className={`text-xs font-medium ${CATEGORY_TEXT[category]}`}>
          {CATEGORY_LABEL[category]}
        </Text>
      </View>
      <View className="bg-gray-50 rounded-full px-2.5 py-0.5">
        <Text className="text-xs text-gray-400">{DIFFICULTY_LABEL[difficulty]}</Text>
      </View>
    </View>
  )
}
