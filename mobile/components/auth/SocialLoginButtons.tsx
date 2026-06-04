import * as Linking from 'expo-linking'
import * as WebBrowser from 'expo-web-browser'
import { Pressable, Text, View } from 'react-native'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/v1'

WebBrowser.maybeCompleteAuthSession()

type Provider = 'google' | 'github' | 'kakao'

async function openOAuth(provider: Provider) {
  const url = `${BASE_URL}/auth/${provider}?platform=mobile`
  await WebBrowser.openAuthSessionAsync(url, 'aipulse://auth/callback')
}

function useOAuthLogin() {
  const { setAuth } = useAuthStore()

  const handleDeepLink = async (url: string) => {
    const parsed = Linking.parse(url)
    const code = parsed.queryParams?.code as string | undefined

    if (!code) return

    try {
      // 일회용 코드를 서버에서 JWT로 교환
      const tokens = await api.exchangeAuthCode(code)
      const me = await api.getMe(tokens.access_token)
      setAuth(tokens.access_token, me)
    } catch {
      // 코드 만료 또는 서버 오류 — 사용자에게 재시도 유도
    }
  }

  const login = async (provider: Provider) => {
    const subscription = Linking.addEventListener('url', ({ url }) => {
      if (url.startsWith('aipulse://auth/callback')) {
        subscription.remove()
        handleDeepLink(url)
      }
    })

    await openOAuth(provider)
    subscription.remove()
  }

  return { login }
}

const PROVIDERS: { id: Provider; label: string; bg: string; text: string }[] = [
  { id: 'google', label: 'Google로 로그인', bg: 'bg-white border border-gray-200', text: 'text-gray-700' },
  { id: 'github', label: 'GitHub로 로그인', bg: 'bg-gray-900', text: 'text-white' },
  { id: 'kakao', label: '카카오로 로그인', bg: 'bg-yellow-400', text: 'text-gray-900' },
]

export default function SocialLoginButtons() {
  const { login } = useOAuthLogin()

  return (
    <View className="w-full gap-3 px-8">
      {PROVIDERS.map(({ id, label, bg, text }) => (
        <Pressable
          key={id}
          onPress={() => login(id)}
          className={`${bg} rounded-2xl py-3.5 items-center active:opacity-70`}
        >
          <Text className={`text-sm font-semibold ${text}`}>{label}</Text>
        </Pressable>
      ))}
    </View>
  )
}
