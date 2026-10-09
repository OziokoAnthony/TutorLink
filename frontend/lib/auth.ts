import api from '@/lib/api'
import { toTutorProfile, type OfferInput } from '@/lib/tutors'
import type { ParentProfile, Role, TutorToRate, UserMe } from '@/types'

/** What a new parent or tutor tells us about themselves. */
export interface ProfileInput {
  role: 'parent' | 'tutor'
  // Parents give a full name; tutors give first name and surname, as on their NIN record.
  full_name?: string
  first_name?: string
  middle_name?: string // tutors: only if their NIN record has one (spec 4 R3.1)
  surname?: string
  phone?: string
  address?: string
  // Tutors: area and at least one offer
  area?: string
  bio?: string
  offers?: OfferInput[]
}

/** Sign-up with any email and a chosen password, for parents and tutors (spec 4 R1.1). */
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

/** Creates a parent or tutor account with any email and a chosen password; they log in afterwards. */
export async function register(input: RegisterInput): Promise<void> {
  await api.post<RawMe>('/auth/register', input)
}

// Signing in: the backend sets the httpOnly login cookie, so nothing here touches the token.

/** Creates the account from a Google sign-in, for parents and tutors, and signs them in at once. */
export async function registerWithGoogle(input: GoogleRegisterInput): Promise<void> {
  await api.post('/auth/google/register', input)
}

export async function login(email: string, password: string): Promise<void> {
  await api.post('/auth/login', { email, password })
}

/** Parents and tutors. 404 when no account uses this Google email; admins get a 401. */
export async function loginWithGoogle(idToken: string): Promise<void> {
  await api.post('/auth/google/login', { id_token: idToken })
}

/** Emails a reset link if an account uses this email. The answer is the same either way. */
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

/** Removes this browser's login cookie. */
export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}
