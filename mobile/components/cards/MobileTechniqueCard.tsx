import { useState } from 'react'
import { Linking, Pressable, Text, View } from 'react-native'
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated'
import type { TechniqueCard } from '@/lib/types'
import { CardBadges } from './CardBadges'
import { MobileTechniqueCardExpanded } from './MobileTechniqueCardExpanded'

interface Props {
  card: TechniqueCard
}

export function MobileTechniqueCard({ card }: Props) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [contentHeight, setContentHeight] = useState(0)
  const height = useSharedValue(0)

  const animatedStyle = useAnimatedStyle(() => ({
    height: height.value,
    overflow: 'hidden',
  }))

  const onMeasure = (h: number) => {
    if (contentHeight === 0 && h > 0) {
      setContentHeight(h)
    }
  }

  const toggle = () => {
    if (isExpanded) {
      height.value = withTiming(0, { duration: 250 })
      setIsExpanded(false)
    } else {
      const target = contentHeight > 0 ? contentHeight : 500
      height.value = withTiming(target, { duration: 250 })
      setIsExpanded(true)
    }
  }

  return (
    <Pressable onPress={toggle} className="p-4">
      <CardBadges
        cardType={card.card_type}
        category={card.category}
        difficulty={card.difficulty}
      />

      <Text
        className="text-sm font-semibold text-gray-900 leading-snug mt-2 mb-1.5"
        numberOfLines={2}
      >
        {card.title}
      </Text>

      <Text className="text-xs text-gray-500 leading-relaxed" numberOfLines={2}>
        {card.problem}
      </Text>

      <View className="flex-row items-center justify-between mt-3">
        <View className="flex-row flex-wrap gap-1 flex-1 mr-2">
          {card.tags.slice(0, 3).map((t) => (
            <Text key={t.slug} className="text-xs text-blue-500">
              #{t.name}
            </Text>
          ))}
        </View>
        <View className="flex-row items-center gap-2">
          <Text className="text-xs text-gray-300">
            {new Date(card.published_at).toLocaleDateString('ko-KR', {
              month: 'short',
              day: 'numeric',
            })}
          </Text>
          <Text className="text-xs text-gray-400">{isExpanded ? '▲' : '▼'}</Text>
        </View>
      </View>

      <Animated.View style={animatedStyle}>
        <MobileTechniqueCardExpanded
          card={card}
          onLayout={onMeasure}
          onOpenSource={() => Linking.openURL(card.source_url)}
        />
      </Animated.View>
    </Pressable>
  )
}
