import type { PublicLevel, PublicReview, PublicStats, PublicSubject, PublicSubjectDetail } from '@/types'

/**
 * Public pages' data (spec 14), fetched on the server so search engines see it, and cached for an hour so a
 * sleeping API doesn't slow every visit (R6.4). On the server the API is reached directly: API_PROXY_TARGET on the
 * free hosting addresses, or NEXT_PUBLIC_API_URL when that is a full address (local development).
 */
function apiBase(): string {
  if (typeof window !== 'undefined') return (process.env.NEXT_PUBLIC_API_URL || '/api/v1').replace(/\/+$/, '')
  const target = (process.env.API_PROXY_TARGET || '').replace(/\/+$/, '')
  if (target) return `${target}/v1`
  const url = process.env.NEXT_PUBLIC_API_URL || ''
  return url.startsWith('http') ? url.replace(/\/+$/, '') : 'http://localhost:8000/v1'
}

const HOUR = 3600

const STARTING = 'TutorLink is starting up. Please refresh in a moment.'

/** null when the subject or level doesn't exist; an error page (cached pages stay up) when the API can't answer. */
async function get<T>(path: string): Promise<T | null> {
  let response: Response
  try {
    response = await fetch(`${apiBase()}/public${path}`, { next: { revalidate: HOUR } })
  } catch {
    throw new Error(STARTING)
  }
  if (response.status === 404 || response.status === 422) return null
  if (!response.ok) throw new Error(STARTING)
  return (await response.json()) as T
}

const money = (v: unknown) => (v === null || v === undefined ? null : Number(v))

export async function publicStats(): Promise<PublicStats | null> {
  return get<PublicStats>('/stats')
}

export async function publicReviews(): Promise<PublicReview[]> {
  return (await get<PublicReview[]>('/reviews')) ?? []
}

export async function publicSubjects(): Promise<PublicSubject[]> {
  return (await get<PublicSubject[]>('/subjects')) ?? []
}

export async function publicSubject(slug: string): Promise<PublicSubjectDetail | null> {
  const s = await get<PublicSubjectDetail>(`/subjects/${encodeURIComponent(slug)}`)
  return s && { ...s, levels: s.levels.map((l) => ({ ...l, min_price: money(l.min_price), max_price: money(l.max_price) })) }
}

export async function publicLevel(level: string): Promise<PublicLevel | null> {
  const l = await get<PublicLevel>(`/levels/${encodeURIComponent(level)}`)
  return l && { ...l, subjects: l.subjects.map((s) => ({ ...s, min_price: money(s.min_price), max_price: money(s.max_price) })) }
}
