import api from '@/lib/api'
import type { AdminDashboard, TeamActivityEntry } from '@/types'

/** The logged-in admin's welcome, last session and recent actions (spec 8 R4.1, R4.2). */
export async function getAdminDashboard(): Promise<AdminDashboard> {
  const { data } = await api.get<AdminDashboard>('/admin/dashboard')
  return data
}

/** Super admin only: the other admins' latest actions, or one admin's (spec 8 R4.3). */
export async function getTeamActivity(adminId?: string): Promise<TeamActivityEntry[]> {
  const { data } = await api.get<TeamActivityEntry[]>('/admin/activity', { params: adminId ? { admin_id: adminId } : {} })
  return data
}
