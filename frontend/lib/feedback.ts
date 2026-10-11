import api from '@/lib/api'
import type { ChatMessage, Feedback, FeedbackKind } from '@/types'

export async function sendFeedback(kind: FeedbackKind, message: string, transcript?: ChatMessage[]): Promise<Feedback> {
  const { data } = await api.post<Feedback>('/feedback', { kind, message, transcript })
  return data
}

export async function getMyFeedback(): Promise<Feedback[]> {
  const { data } = await api.get<Feedback[]>('/feedback/me')
  return data
}

/** The help assistant's answer to the conversation so far (which ends with the user's question). */
export async function askHelp(messages: ChatMessage[]): Promise<string> {
  const { data } = await api.post<{ reply: string }>('/help/chat', { messages })
  return data.reply
}

export async function getAdminFeedback(answered: boolean): Promise<Feedback[]> {
  const { data } = await api.get<Feedback[]>('/admin/feedback', { params: { answered } })
  return data
}

export async function replyToFeedback(id: string, reply: string): Promise<Feedback> {
  const { data } = await api.post<Feedback>(`/admin/feedback/${id}/reply`, { reply })
  return data
}
