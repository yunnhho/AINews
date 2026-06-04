import Constants from 'expo-constants'
import * as Notifications from 'expo-notifications'
import { Platform } from 'react-native'
import { api } from './api'

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
})

export async function registerForPushNotifications(token: string): Promise<string | null> {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#FF231F7C',
    })
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync()
  let finalStatus = existingStatus

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync()
    finalStatus = status
  }

  if (finalStatus !== 'granted') {
    return null
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId
  if (!projectId) {
    console.warn('Expo projectId not found — push token 등록 생략')
    return null
  }

  const { data: expoPushToken } = await Notifications.getExpoPushTokenAsync({ projectId })

  try {
    await api.registerPushToken(token, expoPushToken)
  } catch (e) {
    console.warn('Push token 서버 등록 실패:', e)
  }

  return expoPushToken
}

export async function unregisterPushNotifications(
  authToken: string,
  expoPushToken: string
): Promise<void> {
  try {
    await api.togglePushNotifications(authToken, expoPushToken, false)
  } catch (e) {
    console.warn('Push 알림 비활성화 실패:', e)
  }
}
