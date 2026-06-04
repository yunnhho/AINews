import { useCallback, useEffect, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  Text,
  View,
} from 'react-native'
import { api } from '@/lib/api'
import type { Card, NewsCard, TechniqueCard } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'
import { MobileNewsCard } from '@/components/cards/MobileNewsCard'
import { MobileTechniqueCard } from '@/components/cards/MobileTechniqueCard'
import { SwipeableCard } from '@/components/cards/SwipeableCard'

const CATEGORY_TABS = [
  { label: '전체', value: 'all' },
  { label: '프로그래밍', value: 'CODING' },
  { label: '디자인', value: 'DESIGN' },
  { label: '일반', value: 'GENERAL' },
]

const TYPE_TABS = [
  { label: '전체', value: 'all' },
  { label: '뉴스', value: 'NEWS' },
  { label: '기법', value: 'TECHNIQUE' },
]

function CardSkeleton() {
  return (
    <View className="bg-white mx-4 mb-3 rounded-2xl border border-gray-100 p-4">
      <View className="flex-row gap-2 mb-3">
        <View className="h-5 w-14 bg-gray-100 rounded-full" />
        <View className="h-5 w-20 bg-gray-100 rounded-full" />
      </View>
      <View className="h-4 bg-gray-100 rounded mb-2 w-4/5" />
      <View className="h-3 bg-gray-100 rounded mb-1" />
      <View className="h-3 bg-gray-100 rounded w-3/4" />
    </View>
  )
}

export default function FeedScreen() {
  const { token } = useAuthStore()

  const [category, setCategory] = useState('all')
  const [cardType, setCardType] = useState('all')
  const [cards, setCards] = useState<Card[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    setCards([])
    setCursor(null)
    setHasMore(true)
    setLoading(true)
    api
      .getCards(
        {
          ...(category !== 'all' && { category }),
          ...(cardType !== 'all' && { card_type: cardType }),
          limit: 20,
        },
        token ?? undefined
      )
      .then((res) => {
        setCards(res.items)
        setCursor(res.next_cursor)
        setHasMore(res.has_more)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [category, cardType, token])

  const onRefresh = async () => {
    setRefreshing(true)
    try {
      const res = await api.getCards(
        {
          ...(category !== 'all' && { category }),
          ...(cardType !== 'all' && { card_type: cardType }),
          limit: 20,
        },
        token ?? undefined
      )
      setCards(res.items)
      setCursor(res.next_cursor)
      setHasMore(res.has_more)
    } catch {
      // silent fail
    } finally {
      setRefreshing(false)
    }
  }

  const onEndReached = async () => {
    if (!hasMore || loadingMore || loading) return
    setLoadingMore(true)
    try {
      const res = await api.getCards(
        {
          ...(category !== 'all' && { category }),
          ...(cardType !== 'all' && { card_type: cardType }),
          limit: 20,
          ...(cursor ? { cursor } : {}),
        },
        token ?? undefined
      )
      setCards((prev) => [...prev, ...res.items])
      setCursor(res.next_cursor)
      setHasMore(res.has_more)
    } catch {
      // silent fail
    } finally {
      setLoadingMore(false)
    }
  }

  const handleBookmark = useCallback(
    async (card: Card) => {
      if (!token) return
      setCards((prev) => prev.filter((c) => c.id !== card.id))
      try {
        await api.bookmarkCard(card.id, token)
      } catch {
        setCards((prev) => {
          const exists = prev.some((c) => c.id === card.id)
          return exists ? prev : [card, ...prev]
        })
      }
    },
    [token]
  )

  const handleSkip = useCallback((cardId: number) => {
    setCards((prev) => prev.filter((c) => c.id !== cardId))
  }, [])

  return (
    <View className="flex-1 bg-gray-50">
      {/* 카테고리 탭 */}
      <View className="bg-white border-b border-gray-100">
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={CATEGORY_TABS}
          keyExtractor={(item) => item.value}
          contentContainerClassName="px-4 py-2 gap-2"
          renderItem={({ item }) => (
            <Pressable
              onPress={() => setCategory(item.value)}
              className={`px-3 py-1.5 rounded-full ${
                category === item.value ? 'bg-blue-500' : 'bg-gray-100'
              }`}
            >
              <Text
                className={`text-sm font-medium ${
                  category === item.value ? 'text-white' : 'text-gray-600'
                }`}
              >
                {item.label}
              </Text>
            </Pressable>
          )}
        />
      </View>

      {/* 타입 필터 */}
      <View className="flex-row px-4 py-2 gap-2 bg-white border-b border-gray-100">
        {TYPE_TABS.map((t) => (
          <Pressable
            key={t.value}
            onPress={() => setCardType(t.value)}
            className={`px-3 py-1 rounded-full border ${
              cardType === t.value
                ? 'bg-gray-900 border-gray-900'
                : 'bg-white border-gray-200'
            }`}
          >
            <Text
              className={`text-xs font-medium ${
                cardType === t.value ? 'text-white' : 'text-gray-600'
              }`}
            >
              {t.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {/* 카드 리스트 */}
      {loading ? (
        <View className="pt-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </View>
      ) : cards.length === 0 ? (
        <View className="flex-1 items-center justify-center">
          <Text className="text-4xl mb-3">📭</Text>
          <Text className="text-sm text-gray-400">카드가 없습니다.</Text>
        </View>
      ) : (
        <FlatList
          data={cards}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <SwipeableCard
              card={item}
              token={token}
              onBookmark={handleBookmark}
              onSkip={handleSkip}
            >
              {item.card_type === 'NEWS' ? (
                <MobileNewsCard card={item as NewsCard} />
              ) : (
                <MobileTechniqueCard card={item as TechniqueCard} />
              )}
            </SwipeableCard>
          )}
          contentContainerClassName="pt-3 pb-6"
          onEndReached={onEndReached}
          onEndReachedThreshold={0.3}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          ListFooterComponent={
            loadingMore ? (
              <ActivityIndicator size="small" color="#9CA3AF" className="py-4" />
            ) : null
          }
        />
      )}
    </View>
  )
}
