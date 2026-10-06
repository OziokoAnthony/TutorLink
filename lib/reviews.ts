import api from '@/lib/api'
import type { Review } from '@/types'

/** Create or update my rating of a tutor (`tutorId` is the tutor's user id). */
export async function rateTutor(tutorId: string, rating: number, comment?: string): Promise<void> {
  await api.put(`/tutors/${tutorId}/reviews`, { rating, comment: comment?.trim() || null })
}

export async function getReviews(tutorId: string): Promise<Review[]> {
  const { data } = await api.get<Review[]>(`/tutors/${tutorId}/reviews`, { params: { limit: 50 } })
  return data.map((r) => ({ ...r, comment: r.comment ?? undefined }))
}
