import api from '@/lib/api'
import type { Level, TutorFiltersValue, TutorProfile, TutorSubject } from '@/types'

// The backend sends money and averages as decimal strings ("5000.00"); pages get numbers.
export interface RawTutorProfile extends Omit<TutorProfile, 'rate_per_session' | 'average_rating' | 'vetting_status'> {
  rate_per_session: string
  average_rating: string | null
  vetting_status?: TutorProfile['vetting_status']
}

export function toTutorProfile(raw: RawTutorProfile): TutorProfile {
  return {
    ...raw,
    phone: raw.phone ?? undefined,
    bio: raw.bio ?? undefined,
    vetting_note: raw.vetting_note ?? undefined,
    // The public endpoints only ever return approved tutors and omit the field.
    vetting_status: raw.vetting_status ?? 'approved',
    rate_per_session: Number(raw.rate_per_session),
    average_rating: raw.average_rating === null ? null : Number(raw.average_rating),
    rating_count: raw.rating_count ?? 0,
  }
}

export interface TutorProfileInput {
  full_name: string
  phone?: string
  bio?: string
  area: string
  rate_per_session: number
}

/** Approved tutors only (the backend never returns others). */
export async function getTutors(filters: TutorFiltersValue = {}): Promise<TutorProfile[]> {
  const params: Record<string, string> = {}
  if (filters.subject) params.subject = filters.subject
  if (filters.level) params.level = filters.level
  if (filters.area?.trim()) params.area = filters.area.trim()
  if (filters.sort) params.sort = filters.sort
  const { data } = await api.get<RawTutorProfile[]>('/tutors', { params: { ...params, limit: 100 } })
  return data.map(toTutorProfile)
}

/** `id` is the tutor's user id. */
export async function getTutor(id: string): Promise<TutorProfile> {
  const { data } = await api.get<RawTutorProfile>(`/tutors/${id}`)
  return toTutorProfile(data)
}

export async function vetTutor(id: string, status: 'approved' | 'rejected', note?: string): Promise<TutorProfile> {
  const { data } = await api.patch<RawTutorProfile>(`/tutors/${id}/vet`, { status, note: note || null })
  return toTutorProfile(data)
}

export async function getPendingTutors(): Promise<TutorProfile[]> {
  const { data } = await api.get<RawTutorProfile[]>('/admin/tutors/pending')
  return data.map(toTutorProfile)
}

export async function upsertProfile(input: TutorProfileInput): Promise<TutorProfile> {
  const { data } = await api.post<RawTutorProfile>('/tutors/profile', {
    ...input,
    phone: input.phone || null,
    bio: input.bio || null,
  })
  return toTutorProfile(data)
}

export async function addSubject(subject: string, level: Level): Promise<TutorSubject> {
  const { data } = await api.post<TutorSubject>('/tutors/profile/subjects', { subject, level })
  return data
}

export async function removeSubject(id: string): Promise<void> {
  await api.delete(`/tutors/profile/subjects/${id}`)
}
