import Cookies from 'js-cookie'
import api, { TOKEN_COOKIE } from '@/lib/api'
import { toTutorProfile, type OfferInput } from '@/lib/tutors'
import type { ParentProfile, Role, TutorToRate, UserMe } from '@/types'

/** What a new parent or tutor tells us about themselves. */
export interface ProfileInput {
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

/** Email and password sign-up: parents only. Tutors register with Google (spec 4 R1.1). */
export interface RegisterInput extends ProfileInput {
  email: string
  password: string
}

/** Sign-up with Google: the email is the one in the Google ID token. */
export interface GoogleRegisterInput extends ProfileInput {
  id_token: string
  use_google_photo?: boolean
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

function storeToken(accessToken: string): void {
  Cookies.set(TOKEN_COOKIE, accessToken, {
    expires: 1,
    sameSite: 'strict',
    secure: window.location.protocol === 'https:',
  })
}

/** Creates a parent account with email and password; they log in afterwards. */
export async function register(input: RegisterInput): Promise<void> {
  await api.post<RawMe>('/auth/register', input)
}

/**
 * Creates the account from a Google sign-in. A parent is signed in at once. A tutor gets their work
 * email and generated password, shown once (spec 4 R1.2), and logs in with them.
 */
export async function registerWithGoogle(input: GoogleRegisterInput): Promise<{ work_email: string | null; password: string | null }> {
  const { data } = await api.post<RawMe & { password: string | null; access_token: string | null }>('/auth/google/register', input)
  if (data.access_token) storeToken(data.access_token)
  return { work_email: data.user.work_email ?? null, password: data.password ?? null }
}

/** Logs in and stores the JWT cookie. */
export async function login(email: string, password: string): Promise<void> {
  const { data } = await api.post<{ access_token: string; token_type: string }>('/auth/login', { email, password })
  storeToken(data.access_token)
}

/** Parents only. 404 when no account uses this Google email; tutors get a 401 naming their work email. */
export async function loginWithGoogle(idToken: string): Promise<void> {
  const { data } = await api.post<{ access_token: string; token_type: string }>('/auth/google/login', { id_token: idToken })
  storeToken(data.access_token)
}

/** Emails a reset link if an account uses this personal email. The answer is the same either way. */
export async function forgotPassword(email: string): Promise<void> {
  await api.post('/auth/forgot-password', { email })
}

/** Sets a new password from the emailed link (works once, for 1 hour). */
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await api.post('/auth/reset-password', { token, new_password: newPassword })
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

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await api.put('/auth/me/password', { current_password: currentPassword, new_password: newPassword })
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
