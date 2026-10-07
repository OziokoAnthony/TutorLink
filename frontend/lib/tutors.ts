import api from '@/lib/api'
import { numbers } from '@/lib/convert'
import type { Level, Offer, TutorAvailability, TutorFiltersValue, TutorProfile, WeeklyTime } from '@/types'

export function toOffer(raw: unknown): Offer {
  return numbers<Offer>(raw, ['price'])
}

export function toTutorProfile(raw: unknown): TutorProfile {
  const t = numbers<TutorProfile>(raw, ['price_from', 'average_rating'])
  return {
    ...t,
    phone: t.phone ?? undefined,
    bio: t.bio ?? undefined,
    vetting_note: t.vetting_note ?? undefined,
    // The public endpoints only ever return approved tutors and omit the field.
    vetting_status: t.vetting_status ?? 'approved',
    photo_url: t.photo_url ?? null,
    offers: (t.offers ?? []).map(toOffer),
    rating_count: t.rating_count ?? 0,
  }
}

export interface OfferInput {
  subjects: string[]
  level: Level
  windows: WeeklyTime[]
  price: number
}

export interface TutorProfileInput {
  full_name: string
  phone?: string
  bio?: string
  area: string
}

/** Approved tutors only (the backend never returns others). */
export async function getTutors(filters: TutorFiltersValue = {}): Promise<TutorProfile[]> {
  const params: Record<string, string> = {}
  if (filters.subject) params.subject = filters.subject
  if (filters.level) params.level = filters.level
  if (filters.area?.trim()) params.area = filters.area.trim()
  if (filters.sort) params.sort = filters.sort
  const { data } = await api.get<unknown[]>('/tutors', { params: { ...params, limit: 100 } })
  return data.map(toTutorProfile)
}

/** `id` is the tutor's user id. */
export async function getTutor(id: string): Promise<TutorProfile> {
  const { data } = await api.get(`/tutors/${id}`)
  return toTutorProfile(data)
}

/** When the tutor is booked, when they're free, and whether they're teaching right now. */
export async function getAvailability(id: string): Promise<TutorAvailability> {
  const { data } = await api.get<TutorAvailability>(`/tutors/${id}/schedule`)
  return data
}

export async function vetTutor(id: string, status: 'approved' | 'rejected', note?: string): Promise<TutorProfile> {
  const { data } = await api.patch(`/tutors/${id}/vet`, { status, note: note || null })
  return toTutorProfile(data)
}

export async function getPendingTutors(): Promise<TutorProfile[]> {
  const { data } = await api.get<unknown[]>('/admin/tutors/pending')
  return data.map(toTutorProfile)
}

export async function upsertProfile(input: TutorProfileInput): Promise<TutorProfile> {
  const { data } = await api.post('/tutors/profile', { ...input, phone: input.phone || null, bio: input.bio || null })
  return toTutorProfile(data)
}

export async function getMyOffers(): Promise<Offer[]> {
  const { data } = await api.get<unknown[]>('/tutors/profile/offers')
  return data.map(toOffer)
}

export async function createOffer(input: OfferInput): Promise<Offer> {
  const { data } = await api.post('/tutors/profile/offers', input)
  return toOffer(data)
}

export async function updateOffer(id: string, input: OfferInput): Promise<Offer> {
  const { data } = await api.put(`/tutors/profile/offers/${id}`, input)
  return toOffer(data)
}

export async function removeOffer(id: string): Promise<void> {
  await api.delete(`/tutors/profile/offers/${id}`)
}
