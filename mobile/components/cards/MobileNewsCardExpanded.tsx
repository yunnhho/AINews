import { Pressable, Text, View } from 'react-native'
import type { NewsCard } from '@/lib/types'

interface Props {
  card: NewsCard
  onLayout: (height: number) => void
  onOpenSource: () => void
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View className="mb-4">
      <Text className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
        {title}
      </Text>
      {children}
    </View>
  )
}

export function MobileNewsCardExpanded({ card, onLayout, onOpenSource }: Props) {
  return (
    <View
      className="pt-4 border-t border-gray-100 mt-3"
      onLayout={(e) => onLayout(e.nativeEvent.layout.height + 12)}
    >
      <Section title="What">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.summary}</Text>
      </Section>

      {card.key_points.length > 0 && (
        <Section title="Why it matters">
          {card.key_points.slice(0, 3).map((point, i) => (
            <View key={i} className="flex-row gap-2 mb-1.5">
              <Text className="text-blue-400 text-sm">•</Text>
              <Text className="text-sm text-gray-700 leading-relaxed flex-1">{point}</Text>
            </View>
          ))}
        </Section>
      )}

      {card.key_points.length > 3 && (
        <Section title="Impact">
          {card.key_points.slice(3).map((point, i) => (
            <View key={i} className="flex-row gap-2 mb-1.5">
              <Text className="text-indigo-400 text-sm">→</Text>
              <Text className="text-sm text-gray-700 leading-relaxed flex-1">{point}</Text>
            </View>
          ))}
        </Section>
      )}

      <Pressable
        onPress={onOpenSource}
        className="flex-row items-center gap-1.5 bg-gray-50 rounded-xl px-3 py-2.5 active:opacity-70"
      >
        <Text className="text-sm">🔗</Text>
        <Text className="text-xs text-gray-600 flex-1" numberOfLines={1}>
          {card.source_name}
        </Text>
        <Text className="text-xs text-blue-500">원문 보기</Text>
      </Pressable>
    </View>
  )
}
