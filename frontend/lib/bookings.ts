import api from '@/lib/api'
import { numbers } from '@/lib/convert'
import type { Booking, BookingInput, BookingStatus, Period, Refund } from '@/types'

const MONEY = ['price', 'parent_price_per_lesson', 'tutor_fee_rate', 'tutor_earning_per_lesson',
  'parent_fee_rate', 'platform_margin_per_lesson'] as const

export function toBooking(raw: unknown): Booking {
  const b = numbers<Booking>(raw, MONEY)
  return { ...b, periods: b.periods?.map((p) => numbers<Period>(p, ['amount'])) }
}

export function toRefund(raw: unknown): Refund {
  return numbers<Refund>(raw, ['amount'])
}

export async function requestBooking(input: BookingInput): Promise<Booking> {
  const { data } = await api.post('/bookings', input)
  return toBooking(data)
}

/** Parent: my bookings. */
export async function getMyBookings(): Promise<Booking[]> {
  const { data } = await api.get<unknown[]>('/bookings/me')
  return data.map(toBooking)
}

/** Tutor: requests and bookings with me. */
export async function getTutorBookings(): Promise<Booking[]> {
  const { data } = await api.get<unknown[]>('/bookings/tutor/me')
  return data.map(toBooking)
}

export async function acceptBooking(id: string): Promise<Booking> {
  const { data } = await api.post(`/bookings/${id}/accept`)
  return toBooking(data)
}

export async function declineBooking(id: string, note?: string): Promise<Booking> {
  const { data } = await api.post(`/bookings/${id}/decline`, { note: note || null })
  return toBooking(data)
}

/** Tutor: the video call link for an online booking. */
export async function setMeetingLink(id: string, meetingLink: string): Promise<Booking> {
  const { data } = await api.put(`/bookings/${id}/meeting-link`, { meeting_link: meetingLink })
  return toBooking(data)
}

/** Parent cancels: lessons at least 48 h away are refunded (agreed price, fee excluded) after admin approval. */
export async function cancelBooking(id: string, note?: string): Promise<Booking> {
  const { data } = await api.post(`/bookings/${id}/cancel`, { note: note || null })
  return toBooking(data)
}

/** Either side stops the booking renewing; paid lessons still happen. */
export async function endBooking(id: string, note?: string): Promise<Booking> {
  const { data } = await api.post(`/bookings/${id}/end`, { note: note || null })
  return toBooking(data)
}

export async function getAllBookings(status?: BookingStatus): Promise<Booking[]> {
  const { data } = await api.get<unknown[]>('/admin/bookings', { params: status ? { status } : {} })
  return data.map(toBooking)
}

export async function getRefunds(status?: Refund['status']): Promise<Refund[]> {
  const { data } = await api.get<unknown[]>('/admin/refunds', { params: status ? { status } : {} })
  return data.map(toRefund)
}

export async function decideRefund(id: string, approve: boolean, note?: string): Promise<Refund> {
  const { data } = await api.post(`/admin/refunds/${id}/${approve ? 'approve' : 'reject'}`, { note: note || null })
  return toRefund(data)
}
