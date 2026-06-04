import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  Text,
  View,
} from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { api } from '@/lib/api'
import type { Card, NewsCard, TechniqueCard } from '@/lib/types'
import { useAuthStore } from '@/stores/auth'

const CATEGORY_LABEL: Record<string, string> = {
  CODING: '프로그래밍',
  DESIGN: '디자인',
  GENERAL: '일반',
}
const DIFFICULTY_LABEL: Record<string, string> = {
  BEGINNER: '초급',
  INTERMEDIATE: '중급',
  ADVANCED: '고급',
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="mb-5">
      <Text className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
        {title}
      </Text>
      {children}
    </View>
  )
}

function NewsDetail({ card }: { card: NewsCard }) {
  return (
    <>
      <Section title="요약">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.summary}</Text>
      </Section>
      {card.key_points.length > 0 && (
        <Section title="핵심 포인트">
          {card.key_points.map((point, i) => (
            <View key={i} className="flex-row gap-2 mb-1.5">
              <Text className="text-blue-400 text-sm">•</Text>
              <Text className="text-sm text-gray-700 leading-relaxed flex-1">{point}</Text>
            </View>
          ))}
        </Section>
      )}
    </>
  )
}

function TechniqueDetail({ card }: { card: TechniqueCard }) {
  return (
    <>
      <Section title="문제">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.problem}</Text>
      </Section>
      <Section title="아이디어">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.idea}</Text>
      </Section>
      {card.code_snippet && (
        <Section title="코드">
          <View className="bg-gray-900 rounded-xl p-4">
            <Text className="text-xs text-green-300 font-mono leading-relaxed">
              {card.code_snippet}
            </Text>
          </View>
        </Section>
      )}
      {card.caveats.length > 0 && (
        <Section title="주의점">
          {card.caveats.map((c, i) => (
            <View key={i} className="flex-row gap-2 mb-1.5">
              <Text className="text-yellow-500 text-sm">⚠️</Text>
              <Text className="text-sm text-gray-700 leading-relaxed flex-1">{c}</Text>
            </View>
          ))}
        </Section>
      )}
      {card.prerequisites && (
        <Section title="선행 지식">
          <Text className="text-sm text-gray-500">{card.prerequisites}</Text>
        </Section>
      )}
    </>
  )
}

export default function CardDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>()
  const { token } = useAuthStore()
  const [card, setCard] = useState<Card | null>(null)
  const [loading, setLoading] = useState(true)
  const [liked, setLiked] = useState(false)
  const [bookmarked, setBookmarked] = useState(false)

  useEffect(() => {
    if (!id) return
    api
      .getCard(Number(id), token ?? undefined)
      .then((c) => {
        setCard(c)
        setLiked(c.is_liked)
        setBookmarked(c.is_bookmarked)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id, token])

  const toggleLike = async () => {
    if (!token || !card) return
    const next = !liked
    setLiked(next)
    try {
      if (next) await api.likeCard(card.id, token)
      else await api.unlikeCard(card.id, token)
    } catch {
      setLiked(!next) // rollback
    }
  }

  const toggleBookmark = async () => {
    if (!token || !card) return
    const next = !bookmarked
    setBookmarked(next)
    try {
      if (next) await api.bookmarkCard(card.id, token)
      else await api.unbookmarkCard(card.id, token)
    } catch {
      setBookmarked(!next) // rollback
    }
  }

  if (loading) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <ActivityIndicator size="large" color="#9CA3AF" />
      </View>
    )
  }

  if (!card) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <Text className="text-4xl mb-3">😢</Text>
        <Text className="text-sm text-gray-400">카드를 불러올 수 없습니다.</Text>
      </View>
    )
  }

  return (
    <ScrollView className="flex-1 bg-white" contentContainerClassName="p-5 pb-10">
      {/* 뱃지 */}
      <View className="flex-row flex-wrap gap-2 mb-4">
        <View className="bg-gray-100 rounded-full px-3 py-1">
          <Text className="text-xs text-gray-600">
            {card.card_type === 'NEWS' ? '📰 뉴스' : '⚙️ 기법'}
          </Text>
        </View>
        <View className="bg-blue-50 rounded-full px-3 py-1">
          <Text className="text-xs text-blue-600 font-medium">
            {CATEGORY_LABEL[card.category]}
          </Text>
        </View>
        <View className="bg-gray-50 rounded-full px-3 py-1">
          <Text className="text-xs text-gray-400">
            {DIFFICULTY_LABEL[card.difficulty]}
          </Text>
        </View>
      </View>

      {/* 제목 */}
      <Text className="text-lg font-bold text-gray-900 leading-snug mb-1">
        {card.title}
      </Text>

      {/* 소스 + 날짜 */}
      <Text className="text-xs text-gray-400 mb-5">
        {card.source_name} ·{' '}
        {new Date(card.published_at).toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
        })}
      </Text>

      {/* 본문 */}
      {card.card_type === 'NEWS' ? (
        <NewsDetail card={card} />
      ) : (
        <TechniqueDetail card={card as TechniqueCard} />
      )}

      {/* 태그 */}
      {card.tags.length > 0 && (
        <View className="flex-row flex-wrap gap-2 mb-6">
          {card.tags.map((t) => (
            <View key={t.slug} className="bg-blue-50 rounded-full px-3 py-1">
              <Text className="text-xs text-blue-500">#{t.name}</Text>
            </View>
          ))}
        </View>
      )}

      {/* 액션 버튼 */}
      <View className="flex-row gap-3 mt-2">
        <Pressable
          onPress={toggleLike}
          className={`flex-1 flex-row items-center justify-center gap-1.5 py-3 rounded-xl border ${
            liked ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'
          } active:opacity-70`}
        >
          <Text className="text-base">{liked ? '❤️' : '🤍'}</Text>
          <Text className={`text-sm font-medium ${liked ? 'text-red-500' : 'text-gray-500'}`}>
            좋아요
          </Text>
        </Pressable>

        <Pressable
          onPress={toggleBookmark}
          className={`flex-1 flex-row items-center justify-center gap-1.5 py-3 rounded-xl border ${
            bookmarked ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
          } active:opacity-70`}
        >
          <Text className="text-base">{bookmarked ? '🔖' : '📎'}</Text>
          <Text className={`text-sm font-medium ${bookmarked ? 'text-blue-500' : 'text-gray-500'}`}>
            북마크
          </Text>
        </Pressable>

        <Pressable
          onPress={() => Linking.openURL(card.source_url)}
          className="flex-1 flex-row items-center justify-center gap-1.5 py-3 rounded-xl border bg-gray-50 border-gray-200 active:opacity-70"
        >
          <Text className="text-base">🔗</Text>
          <Text className="text-sm font-medium text-gray-500">원문</Text>
        </Pressable>
      </View>
    </ScrollView>
  )
}
