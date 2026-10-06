import type { Level, SessionStatus, InvoiceStatus, VettingStatus } from '@/types'

/** Index matches the backend: 0 = Monday ... 6 = Sunday. */
export const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

export const LEVELS: { value: Level; label: string }[] = [
  { value: 'primary', label: 'Primary' },
  { value: 'junior_secondary', label: 'Junior Secondary' },
  { value: 'senior_secondary', label: 'Senior Secondary' },
]

/** Common Nigerian school subjects, used for the browse filter and as suggestions for tutors. */
export const SUBJECTS = [
  'Mathematics', 'English Language', 'Basic Science', 'Basic Technology', 'Social Studies',
  'Civic Education', 'Physics', 'Chemistry', 'Biology', 'Further Mathematics', 'Economics',
  'Literature in English', 'Government', 'Geography', 'Agricultural Science', 'Computer Studies',
  'Commerce', 'Accounting', 'French', 'Yoruba', 'Igbo', 'Hausa', 'Christian Religious Studies',
  'Islamic Religious Studies', 'Verbal Reasoning', 'Quantitative Reasoning',
]

export function levelLabel(level?: Level): string {
  return LEVELS.find((l) => l.value === level)?.label ?? ''
}

/** ₦3,500 — kobo only shown when present. */
export function formatNaira(amount: number): string {
  return '₦' + amount.toLocaleString('en-NG', {
    minimumFractionDigits: Number.isInteger(amount) ? 0 : 2,
    maximumFractionDigits: 2,
  })
}

/** "15:00:00" -> "15:00" */
export function formatTime(time: string): string {
  return time.slice(0, 5)
}

/** Parses "YYYY-MM-DD" as a local calendar date (no timezone shift). */
export function parseDate(value: string): Date {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/** "2025-10-15" -> "Wednesday, 15 Oct 2025" */
export function formatDate(value: string): string {
  const date = parseDate(value)
  return date.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' })
}

/** Local date as "YYYY-MM-DD". */
export function toISODate(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

/** Today's weekday in the backend's numbering (0 = Monday). */
export function todayDayOfWeek(): number {
  return (new Date().getDay() + 6) % 7
}

/** The most recent date (today or earlier) that falls on `dayOfWeek` (0 = Monday). */
export function latestDateOnWeekday(dayOfWeek: number): string {
  const date = new Date()
  const back = (todayDayOfWeek() - dayOfWeek + 7) % 7
  date.setDate(date.getDate() - back)
  return toISODate(date)
}

export function monthYear(month: number, year: number): string {
  return `${MONTHS[month - 1]} ${year}`
}

export const SESSION_STATUS_LABEL: Record<SessionStatus, string> = {
  scheduled: 'Scheduled', logged: 'Logged', confirmed: 'Confirmed', cancelled: 'Cancelled',
}

export const INVOICE_STATUS_LABEL: Record<InvoiceStatus, string> = {
  pending: 'Pending', paid: 'Paid', failed: 'Failed',
}

export const VETTING_STATUS_LABEL: Record<VettingStatus, string> = {
  pending: 'Under review', approved: 'Approved', rejected: 'Not approved',
}
