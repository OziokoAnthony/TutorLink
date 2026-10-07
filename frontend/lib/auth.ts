import Cookies from 'js-cookie'
import api, { TOKEN_COOKIE } from '@/lib/api'
import { toTutorProfile, type OfferInput } from '@/lib/tutors'
import type { ParentProfile, Role, TutorToRate, UserMe } from '@/types'

export interface RegisterInput {
  email: string
  password: string
  role: 'parent' | 'tutor'
  full_name: string
  phone?: string
  address?: string
  // Tutors: area and at least one offer
  area?: string
  bio?: string
  offers?: OfferInput[]
}

interface RawMe {
  user: { id: string; email: string; role: Role; photo_url: string | null }
  parent_profile: ParentProfile | null
  tutor_profile: unknown | null
  tutors_to_rate: TutorToRate[]
}

export const ROLE_HOME: Record<Role, string> = {
  parent: '/dashboard/parent',
  tutor: '/dashboard/tutor',
  admin: '/admin/tutors',
}

export async function register(input: RegisterInput): Promise<void> {
  await api.post('/auth/register', input)
}

/** Logs in and stores the JWT cookie. */
export async function login(email: string, password: string): Promise<void> {
  const { data } = await api.post<{ access_token: string; token_type: string }>('/auth/login', { email, password })
  Cookies.set(TOKEN_COOKIE, data.access_token, {
    expires: 1,
    sameSite: 'strict',
    secure: window.location.protocol === 'https:',
  })
}

function toUserMe(data: RawMe): UserMe {
  return {
    id: data.user.id,
    email: data.user.email,
    role: data.user.role,
    photo_url: data.user.photo_url ?? null,
    profile: data.tutor_profile ? toTutorProfile(data.tutor_profile) : data.parent_profile,
    tutors_to_rate: data.tutors_to_rate ?? [],
  }
}

export async function getMe(): Promise<UserMe> {
  const { data } = await api.get<RawMe>('/auth/me')
  return toUserMe(data)
}

/** JPG, PNG or WebP up to 5 MB; the backend crops it to a square. */
export async function uploadPhoto(file: File): Promise<UserMe> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.put<RawMe>('/auth/me/photo', form)
  return toUserMe(data)
}

/** Admin: remove an inappropriate profile picture. */
export async function removeUserPhoto(userId: string): Promise<void> {
  await api.delete(`/admin/users/${userId}/photo`)
}

export function logout(): void {
  Cookies.remove(TOKEN_COOKIE)
}

export function hasToken(): boolean {
  return Boolean(Cookies.get(TOKEN_COOKIE))
}
