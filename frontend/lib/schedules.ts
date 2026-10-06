import api from '@/lib/api'
import type { Level, Schedule } from '@/types'

export interface ScheduleInput {
  tutor_id: string
  day_of_week: number
  start_time: string
  end_time: string
  subject: string
  level: Level
}

export async function createSchedule(input: ScheduleInput): Promise<Schedule> {
  const { data } = await api.post<Schedule>('/schedules', input)
  return data
}

/** Parent: my active schedules. */
export async function getMySchedules(): Promise<Schedule[]> {
  const { data } = await api.get<Schedule[]>('/schedules/me')
  return data
}

/** Tutor: my active schedules. */
export async function getTutorSchedules(): Promise<Schedule[]> {
  const { data } = await api.get<Schedule[]>('/schedules/tutor/me')
  return data
}

export async function cancelSchedule(id: string): Promise<Schedule> {
  const { data } = await api.delete<Schedule>(`/schedules/${id}`)
  return data
}
