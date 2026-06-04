import { useEffect, useState } from 'react'
import { Image, Pressable, Switch, Text, View } from 'react-native'
import { useAuthStore } from '@/stores/auth'
import SocialLoginButtons from '@/components/auth/SocialLoginButtons'
import { registerForPushNotifications, unregisterPushNotifications } from '@/lib/notifications'
import { api } from '@/lib/api'

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-row items-center justify-between px-4 py-3 border-b border-gray-100">
      <Text className="text-sm text-gray-500">{label}</Text>
      <Text className="text-sm font-medium text-gray-800">{value}</Text>
    </View>
  )
}

export default function SettingsScreen() {
  const { user, token, clearAuth } = useAuthStore()
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null)
  const [notificationsEnabled, setNotificationsEnabled] = useState(true)

  useEffect(() => {
    if (!token) return
    registerForPushNotifications(token).then((t) => {
      if (t) setExpoPushToken(t)
    })
  }, [token])

  const handleNotificationToggle = async (value: boolean) => {
    setNotificationsEnabled(value)
    if (!token || !expoPushToken) return
    try {
      await api.togglePushNotifications(token, expoPushToken, value)
    } catch (e) {
      console.warn('알림 설정 변경 실패:', e)
      setNotificationsEnabled(!value)
    }
  }

  if (!token || !user) {
    return (
      <View className="flex-1 items-center justify-center bg-gray-50 gap-6">
        <Text className="text-5xl">👤</Text>
        <Text className="text-base font-semibold text-gray-700">로그인이 필요합니다</Text>
        <Text className="text-sm text-gray-400 text-center px-8">
          소셜 로그인 후 좋아요·북마크·추천 피드를 이용할 수 있습니다.
        </Text>
        <SocialLoginButtons />
      </View>
    )
  }

  const providerLabel =
    user.provider === 'google'
      ? 'Google'
      : user.provider === 'github'
      ? 'GitHub'
      : user.provider === 'kakao'
      ? '카카오'
      : user.provider

  return (
    <View className="flex-1 bg-gray-50">
      {/* 프로필 헤더 */}
      <View className="items-center py-8 bg-white border-b border-gray-100">
        {user.avatar_url ? (
          <Image
            source={{ uri: user.avatar_url }}
            className="w-16 h-16 rounded-full mb-3"
          />
        ) : (
          <View className="w-16 h-16 rounded-full bg-blue-100 items-center justify-center mb-3">
            <Text className="text-2xl">👤</Text>
          </View>
        )}
        <Text className="text-lg font-bold text-gray-900">{user.nickname}</Text>
        <Text className="text-sm text-gray-400 mt-0.5">{providerLabel} 로그인</Text>
      </View>

      {/* 계정 정보 */}
      <View className="mt-6 bg-white rounded-2xl mx-4 overflow-hidden">
        <Row label="닉네임" value={user.nickname} />
        <Row label="로그인 방식" value={providerLabel} />
        <Row label="사용자 ID" value={String(user.id)} />
      </View>

      {/* 알림 설정 */}
      <View className="mt-4 bg-white rounded-2xl mx-4 overflow-hidden">
        <View className="flex-row items-center justify-between px-4 py-3">
          <View>
            <Text className="text-sm font-medium text-gray-800">새 카드 알림</Text>
            <Text className="text-xs text-gray-400 mt-0.5">배치 완료 시 신규 카드 알림</Text>
          </View>
          <Switch
            value={notificationsEnabled}
            onValueChange={handleNotificationToggle}
            trackColor={{ false: '#d1d5db', true: '#3b82f6' }}
            thumbColor="#ffffff"
          />
        </View>
      </View>

      {/* 앱 정보 */}
      <View className="mt-4 bg-white rounded-2xl mx-4 overflow-hidden">
        <Row label="버전" value="1.0.0" />
        <Row label="API 서버" value={process.env.EXPO_PUBLIC_API_URL ?? 'localhost'} />
      </View>

      {/* 로그아웃 */}
      <View className="mt-6 mx-4">
        <Pressable
          onPress={clearAuth}
          className="bg-red-50 border border-red-200 rounded-2xl py-3.5 items-center active:opacity-70"
        >
          <Text className="text-sm font-semibold text-red-600">로그아웃</Text>
        </Pressable>
      </View>
    </View>
  )
}
