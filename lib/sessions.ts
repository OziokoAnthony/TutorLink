import api from '@/lib/api'
import type { Session, SessionStatus } from '@/types'

export interface SessionFilters {
  status?: SessionStatus
  month?: number
  year?: number
}

export interface LogSessionInput {
  schedule_id: string
  session_date: string
  topic_covered?: string
  homework?: string
}

function clean(session: Session): Session {
  return {
    ...session,
    topic_covered: session.topic_covered ?? undefined,
    homework: session.homework ?? undefined,
    logged_at: session.logged_at ?? undefined,
    confirmed_at: session.confirmed_at ?? undefined,
  }
}

/** Tutor logs a session they taught. */
export async function logSession(input: LogSessionInput): Promise<Session> {
  const { data } = await api.post<Session>('/sessions', {
    ...input,
    topic_covered: input.topic_covered || null,
    homework: input.homework || null,
  })
  return clean(data)
}

/** Parent: my sessions. */
export async function getMySessions(filters: SessionFilters = {}): Promise<Session[]> {
  const { data } = await api.get<Session[]>('/sessions/me', { params: filters })
  return data.map(clean)
}

/** Tutor: sessions I've logged. */
export async function getTutorSessions(filters: SessionFilters = {}): Promise<Session[]> {
  const { data } = await api.get<Session[]>('/sessions/tutor/me', { params: filters })
  return data.map(clean)
}

export async function confirmSession(id: string): Promise<Session> {
  const { data } = await api.patch<Session>(`/sessions/${id}/confirm`)
  return clean(data)
}
