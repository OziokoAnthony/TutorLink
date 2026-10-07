import Cookies from 'js-cookie'
import api, { TOKEN_COOKIE } from '@/lib/api'
import { toTutorProfile, type OfferInput } from '@/lib/tutors'
import type { ParentProfile, Role, TutorToRate, UserMe } from '@/types'

export interface RegisterInput {
  email: string
  password: string
  role: 'parent' | 'tutor'
  // Parents give a full name; tutors give first name and surname, which make their work email.
  full_name?: string
  first_name?: string
  surname?: string
  phone?: string
  address?: string
  // Tutors: area and at least one offer
  area?: string
  bio?: string
  offers?: OfferInput[]
}

interface RawMe {
  user: { id: string; email: string; work_email: string | null; role: Role; photo_url: string | null }
  parent_profile: ParentProfile | null
  tutor_profile: unknown | null
  tutors_to_rate: TutorToRate[]
}

export const ROLE_HOME: Record<Role, string> = {
  parent: '/dashboard/parent',
  tutor: '/dashboard/tutor',
  admin: '/admin/tutors',
}

/** Creates the account. For a tutor, returns the work email they must log in with. */
export async function register(input: RegisterInput): Promise<{ work_email: string | null }> {
  const { data } = await api.post<RawMe>('/auth/register', input)
  return { work_email: data.user.work_email ?? null }
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
    work_email: data.user.work_email ?? null,
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
