import api from '@/lib/api'
import { numbers } from '@/lib/convert'
import type { IssueKind, IssueResolution, Lesson, LessonStatus } from '@/types'

export function toLesson(raw: unknown): Lesson {
  return numbers<Lesson>(raw, ['price', 'parent_price', 'tutor_earning'])
}

export async function getMyLessons(status?: LessonStatus): Promise<Lesson[]> {
  const { data } = await api.get<unknown[]>('/lessons/me', { params: status ? { status } : {} })
  return data.map(toLesson)
}

export async function getTutorLessons(status?: LessonStatus): Promise<Lesson[]> {
  const { data } = await api.get<unknown[]>('/lessons/tutor/me', { params: status ? { status } : {} })
  return data.map(toLesson)
}

export async function submitReport(id: string, topic_covered: string, homework?: string): Promise<Lesson> {
  const { data } = await api.post(`/lessons/${id}/report`, { topic_covered, homework: homework || null })
  return toLesson(data)
}

export async function reportProblem(id: string, kind: IssueKind, description: string): Promise<Lesson> {
  const { data } = await api.post(`/lessons/${id}/problem`, { kind, description })
  return toLesson(data)
}

export async function getIssues(openOnly = true): Promise<Lesson[]> {
  const { data } = await api.get<unknown[]>('/admin/issues', { params: { open_only: openOnly } })
  return data.map(toLesson)
}

export interface ResolveInput {
  resolution: IssueResolution
  note?: string
  new_date?: string
  new_start_time?: string
  new_end_time?: string
}

export async function resolveIssue(lessonId: string, input: ResolveInput): Promise<Lesson> {
  const { data } = await api.post(`/admin/lessons/${lessonId}/resolve`, { ...input, note: input.note || null })
  return toLesson(data)
}
