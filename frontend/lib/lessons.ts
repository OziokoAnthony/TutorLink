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

/** A viewing link for the lesson's recording; it expires after 15 minutes. */
export async function getRecordingLink(id: string): Promise<{ url: string; expires_at: string }> {
  const { data } = await api.get(`/lessons/${id}/recording`)
  return data
}

/** Uploads an online lesson's recording straight to storage (never through the API), then asks the
 * backend to check it. `onProgress` gets 0-100. */
export async function uploadRecording(id: string, file: File, onProgress: (percent: number) => void): Promise<Lesson> {
  const { data: upload } = await api.post<{ upload_url: string; content_type: string }>(
    `/lessons/${id}/recording/upload`, { filename: file.name, content_type: file.type, size: file.size })
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', upload.upload_url)
    xhr.setRequestHeader('Content-Type', upload.content_type)
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100)) }
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error('The upload failed. Please try again.')))
    xhr.onerror = () => reject(new Error('The upload failed. Check your connection and try again.'))
    xhr.send(file)
  })
  const { data } = await api.post(`/lessons/${id}/recording/complete`)
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
