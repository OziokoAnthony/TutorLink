import api from '@/lib/api'
import type { ActivityBand, UserRow, UsersOverview } from '@/types'

export interface UserFilters {
  role?: 'parent' | 'tutor'
  band?: ActivityBand
  vetting?: 'pending' | 'approved' | 'rejected'
  q?: string
}

/** Spec 10 R3.1, R3.2: counts by role, activity band and tutors' onboarding stage. */
export async function getUsersOverview(): Promise<UsersOverview> {
  const { data } = await api.get<UsersOverview>('/admin/users/overview')
  return data
}

/** Spec 10 R3.3: newest sign-ups first. */
export async function getUsers(filters: UserFilters, skip = 0, limit = 50): Promise<UserRow[]> {
  const params = Object.fromEntries(Object.entries({ ...filters, skip, limit }).filter(([, v]) => v !== undefined && v !== ''))
  const { data } = await api.get<UserRow[]>('/admin/users', { params })
  return data
}

/** Spec 10 R5: the account closes 14 days later, after an admin confirms; a 409 while something is outstanding. */
export async function sendRemovalNotice(id: string, reason: string): Promise<UserRow> {
  const { data } = await api.post<UserRow>(`/admin/users/${id}/notice`, { reason })
  return data
}

export async function cancelRemovalNotice(id: string): Promise<UserRow> {
  const { data } = await api.delete<UserRow>(`/admin/users/${id}/notice`)
  return data
}

export async function removeUser(id: string): Promise<UserRow> {
  const { data } = await api.post<UserRow>(`/admin/users/${id}/remove`)
  return data
}

export async function restoreUser(id: string): Promise<UserRow> {
  const { data } = await api.post<UserRow>(`/admin/users/${id}/restore`)
  return data
}
