import { Pressable, Text, View } from 'react-native'
import type { TechniqueCard } from '@/lib/types'
import { CodeBlock } from '@/components/ui/CodeBlock'

interface Props {
  card: TechniqueCard
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

export function MobileTechniqueCardExpanded({ card, onLayout, onOpenSource }: Props) {
  return (
    <View
      className="pt-4 border-t border-gray-100 mt-3"
      onLayout={(e) => onLayout(e.nativeEvent.layout.height + 12)}
    >
      {/* 1단: 문제 */}
      <Section title="문제">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.problem}</Text>
      </Section>

      {/* 2단: 아이디어 */}
      <Section title="아이디어">
        <Text className="text-sm text-gray-700 leading-relaxed">{card.idea}</Text>
      </Section>

      {/* 3단: 코드 */}
      {card.code_snippet && (
        <Section title="코드">
          <CodeBlock code={card.code_snippet} />
        </Section>
      )}

      {/* 4단: 주의점 */}
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
        <View className="bg-blue-50 rounded-xl px-3 py-2 mb-4">
          <Text className="text-xs font-semibold text-blue-400 mb-0.5">선행 지식</Text>
          <Text className="text-xs text-blue-700">{card.prerequisites}</Text>
        </View>
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
