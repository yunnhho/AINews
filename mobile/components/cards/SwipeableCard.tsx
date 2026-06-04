import { useRef, useState } from 'react'
import { Modal, Pressable, Text, View } from 'react-native'
import { Swipeable } from 'react-native-gesture-handler'
import Animated from 'react-native-reanimated'
import type { Card } from '@/lib/types'

interface Props {
  card: Card
  token: string | null
  onBookmark: (card: Card) => void
  onSkip: (cardId: number) => void
  children: React.ReactNode
}

function BookmarkAction() {
  return (
    <View className="justify-center items-center bg-blue-500 w-24 rounded-r-2xl">
      <Text className="text-2xl mb-1">🔖</Text>
      <Text className="text-white text-xs font-semibold">북마크</Text>
    </View>
  )
}

function SkipAction() {
  return (
    <View className="justify-center items-center bg-gray-300 w-24 rounded-l-2xl">
      <Text className="text-2xl mb-1">→</Text>
      <Text className="text-gray-600 text-xs font-semibold">스킵</Text>
    </View>
  )
}

function LoginModal({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable
        className="flex-1 bg-black/40 justify-center items-center px-8"
        onPress={onClose}
      >
        <Pressable className="bg-white rounded-2xl p-6 w-full max-w-sm" onPress={() => {}}>
          <Text className="text-lg font-bold text-gray-900 mb-2 text-center">
            로그인이 필요합니다
          </Text>
          <Text className="text-sm text-gray-500 text-center mb-5">
            북마크를 저장하려면 로그인이 필요합니다.
          </Text>
          <Pressable
            onPress={onClose}
            className="bg-blue-500 rounded-xl py-3 items-center active:opacity-80"
          >
            <Text className="text-white font-semibold">확인</Text>
          </Pressable>
        </Pressable>
      </Pressable>
    </Modal>
  )
}

export function SwipeableCard({ card, token, onBookmark, onSkip, children }: Props) {
  const ref = useRef<Swipeable>(null)
  const [showLoginModal, setShowLoginModal] = useState(false)

  const handleSwipeOpen = (direction: 'left' | 'right') => {
    if (direction === 'right') {
      // 왼쪽 스와이프 → 오른쪽 액션 → 북마크
      if (!token) {
        ref.current?.close()
        setShowLoginModal(true)
        return
      }
      onBookmark(card)
    } else {
      // 오른쪽 스와이프 → 왼쪽 액션 → 스킵
      onSkip(card.id)
    }
  }

  return (
    <>
      <Swipeable
        ref={ref}
        renderRightActions={() => <BookmarkAction />}
        renderLeftActions={() => <SkipAction />}
        onSwipeableOpen={handleSwipeOpen}
        friction={2}
        leftThreshold={80}
        rightThreshold={80}
        overshootLeft={false}
        overshootRight={false}
      >
        <View className="bg-white mx-4 mb-3 rounded-2xl border border-gray-100">
          {children}

          <View className="flex-row gap-3 px-4 pb-3 pt-1 border-t border-gray-50">
            <Text className="text-xs text-gray-400">❤️ {card.like_count}</Text>
            <Text className="text-xs text-gray-400">🔖 {card.bookmark_count}</Text>
            <Text className="text-xs text-gray-300 ml-auto">{card.source_name}</Text>
          </View>
        </View>
      </Swipeable>

      <LoginModal visible={showLoginModal} onClose={() => setShowLoginModal(false)} />
    </>
  )
}
