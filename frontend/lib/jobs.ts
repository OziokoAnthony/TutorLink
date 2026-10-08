import api from '@/lib/api'
import { toBooking } from '@/lib/bookings'
import { numbers } from '@/lib/convert'
import type { Applicant, Booking, Job, JobFiltersValue, JobInput } from '@/types'

const MONEY = ['price', 'parent_price_per_lesson', 'tutor_fee_rate', 'tutor_earning_per_lesson'] as const

function toJob(raw: unknown): Job {
  return numbers<Job>(raw, MONEY)
}

function toApplicant(raw: unknown): Applicant {
  return numbers<Applicant>(raw, ['average_rating'])
}

// ---------- Parent ----------

export async function postJob(input: JobInput): Promise<Job> {
  const { data } = await api.post('/jobs', input)
  return toJob(data)
}

/** Replaces an open job's details; applicants are told, and any whose times now clash are withdrawn. */
export async function updateJob(id: string, input: JobInput): Promise<Job> {
  const { data } = await api.put(`/jobs/${id}`, input)
  return toJob(data)
}

export async function closeJob(id: string): Promise<Job> {
  const { data } = await api.post(`/jobs/${id}/close`)
  return toJob(data)
}

export async function getMyJobs(): Promise<Job[]> {
  const { data } = await api.get<unknown[]>('/jobs/me')
  return data.map(toJob)
}

export async function getApplicants(jobId: string): Promise<Applicant[]> {
  const { data } = await api.get<unknown[]>(`/jobs/${jobId}/applications`)
  return data.map(toApplicant)
}

/** Books the applicant: the booking is taken at once and waits for the parent's payment. */
export async function chooseApplicant(jobId: string, applicationId: string): Promise<Booking> {
  const { data } = await api.post(`/jobs/${jobId}/applications/${applicationId}/choose`)
  return toBooking(data)
}

// ---------- Both ----------

/** The parent's own job; for an approved tutor, an open job or one they applied to. */
export async function getJob(id: string): Promise<Job> {
  const { data } = await api.get(`/jobs/${id}`)
  return toJob(data)
}

// ---------- Tutor ----------

export async function browseJobs(filters: JobFiltersValue): Promise<Job[]> {
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
  const { data } = await api.get<unknown[]>('/jobs', { params: { ...params, limit: 100 } })
  return data.map(toJob)
}

export async function getMyApplications(): Promise<Job[]> {
  const { data } = await api.get<unknown[]>('/jobs/applications/me')
  return data.map(toJob)
}

export async function applyToJob(id: string, note?: string): Promise<Job> {
  const { data } = await api.post(`/jobs/${id}/apply`, { note: note || null })
  return toJob(data)
}

export async function withdrawFromJob(id: string): Promise<Job> {
  const { data } = await api.post(`/jobs/${id}/withdraw`)
  return toJob(data)
}
