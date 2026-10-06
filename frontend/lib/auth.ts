import Cookies from 'js-cookie'
import api, { TOKEN_COOKIE } from '@/lib/api'
import { toTutorProfile, type RawTutorProfile } from '@/lib/tutors'
import type { ParentProfile, Role, TutorToRate, UserMe } from '@/types'

export interface RegisterInput {
  email: string
  password: string
  role: 'parent' | 'tutor'
  full_name: string
  phone?: string
  address?: string
  area?: string
  rate_per_session?: number
  bio?: string
}

interface RawMe {
  user: { id: string; email: string; role: Role }
  parent_profile: ParentProfile | null
  tutor_profile: RawTutorProfile | null
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

export async function getMe(): Promise<UserMe> {
  const { data } = await api.get<RawMe>('/auth/me')
  return {
    id: data.user.id,
    email: data.user.email,
    role: data.user.role,
    profile: data.tutor_profile ? toTutorProfile(data.tutor_profile) : data.parent_profile,
    tutors_to_rate: data.tutors_to_rate ?? [],
  }
}

export function logout(): void {
  Cookies.remove(TOKEN_COOKIE)
}

export function hasToken(): boolean {
  return Boolean(Cookies.get(TOKEN_COOKIE))
}
