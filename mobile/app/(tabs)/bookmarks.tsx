import { useEffect, useState } from 'react'
import { FlatList, Pressable, Text, View } from 'react-native'
import { useRouter } from 'expo-router'
import { api } from '@/lib/api'
import type { Card } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'

const CATEGORY_COLOR: Record<string, string> = {
  CODING: 'bg-blue-100 text-blue-700',
  DESIGN: 'bg-purple-100 text-purple-700',
  GENERAL: 'bg-green-100 text-green-700',
}

function BookmarkCard({ card, onPress }: { card: Card; onPress: () => void }) {
  const categoryStyle = CATEGORY_COLOR[card.category] ?? 'bg-gray-100 text-gray-600'
  return (
    <Pressable
      onPress={onPress}
      className="bg-white mx-4 mb-3 rounded-2xl border border-gray-100 p-4 active:opacity-70"
    >
      <View className="flex-row gap-1.5 mb-2">
        <View className="bg-gray-100 rounded-full px-2.5 py-0.5">
          <Text className="text-xs text-gray-600">
            {card.card_type === 'NEWS' ? '📰 뉴스' : '⚙️ 기법'}
          </Text>
        </View>
        <View className={`rounded-full px-2.5 py-0.5 ${categoryStyle}`}>
          <Text className="text-xs font-medium">
            {card.category === 'CODING' ? '프로그래밍' : card.category === 'DESIGN' ? '디자인' : '일반'}
          </Text>
        </View>
      </View>
      <Text className="text-sm font-semibold text-gray-900 leading-snug mb-1" numberOfLines={2}>
        {card.title}
      </Text>
      <Text className="text-xs text-gray-500 leading-relaxed" numberOfLines={2}>
        {card.summary}
      </Text>
    </Pressable>
  )
}

export default function BookmarksScreen() {
  const router = useRouter()
  const { token } = useAuthStore()
  const [cards, setCards] = useState<Card[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    api
      .getBookmarks(token)
      .then((res) => setCards(res.items))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [token])

  if (!token) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-50">
        <Text className="text-4xl mb-3">🔐</Text>
        <Text className="text-sm text-gray-500">로그인 후 북마크를 확인할 수 있습니다.</Text>
      </View>
    )
  }

  if (loading) {
    return (
      <View className="flex-1 pt-3 bg-gray-50">
        {Array.from({ length: 4 }).map((_, i) => (
          <View key={i} className="bg-white mx-4 mb-3 rounded-2xl border border-gray-100 p-4">
            <View className="h-4 bg-gray-100 rounded mb-2 w-3/4" />
            <View className="h-3 bg-gray-100 rounded w-full" />
          </View>
        ))}
      </View>
    )
  }

  if (cards.length === 0) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-50">
        <Text className="text-4xl mb-3">🔖</Text>
        <Text className="text-sm text-gray-400">저장된 북마크가 없습니다.</Text>
      </View>
    )
  }

  return (
    <View className="flex-1 bg-gray-50">
      <FlatList
        data={cards}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <BookmarkCard card={item} onPress={() => router.push(`/cards/${item.id}`)} />
        )}
        contentContainerClassName="pt-3 pb-6"
      />
    </View>
  )
}
