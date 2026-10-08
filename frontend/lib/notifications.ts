import api from '@/lib/api'
import type { NotificationList } from '@/types'

export async function getNotifications(): Promise<NotificationList> {
  const { data } = await api.get<NotificationList>('/notifications/me')
  return data
}

export async function markRead(id: string): Promise<void> {
  await api.post(`/notifications/${id}/read`)
}

export async function markAllRead(): Promise<void> {
  await api.post('/notifications/me/read-all')
}
