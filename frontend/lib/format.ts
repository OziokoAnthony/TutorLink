import type {
  ApplicationStatus, BillingPeriod, BookingStatus, CertificateStatus, CertificateType, JobStatus, EarningStatus, FeedbackKind, IssueKind, Level, LessonStatus, PeriodStatus, RefundStatus,
  TransferStatus, VettingStatus, WeeklyTime,
} from '@/types'

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
  { value: 'international', label: 'International High School' },
]

/** Common Nigerian school subjects. Tutors and job posts can only use listed subjects; the backend has the
 * same list (`app/domains/tutors/subjects.py`, kept in step by `tests/test_subjects.py`). */
const NIGERIAN_SUBJECTS = [
  'Mathematics', 'English Language', 'Basic Science', 'Basic Technology', 'Social Studies',
  'Civic Education', 'Physics', 'Chemistry', 'Biology', 'Further Mathematics', 'Economics',
  'Literature in English', 'Government', 'Geography', 'Agricultural Science', 'Computer Studies',
  'Commerce', 'Accounting', 'French', 'Yoruba', 'Igbo', 'Hausa', 'Christian Religious Studies',
  'Islamic Religious Studies', 'Verbal Reasoning', 'Quantitative Reasoning',
]

/** High school subjects of international schools (British IGCSE and A-Level, IB, American) that the
 * Nigerian list doesn't already cover, plus the international exams parents book prep for. */
const INTERNATIONAL_SUBJECTS = [
  'Additional Mathematics', 'Statistics', 'Combined Science', 'Computer Science', 'Business Studies',
  'History', 'Global Perspectives', 'Environmental Management', 'Psychology', 'Sociology',
  'English as a Second Language', 'Spanish', 'German', 'Mandarin Chinese', 'Art and Design',
  'Design and Technology', 'Music', 'Physical Education', 'IB Theory of Knowledge',
  'AP Calculus', 'SAT', 'ACT', 'IELTS', 'TOEFL',
]

export const SUBJECTS = [...NIGERIAN_SUBJECTS, ...INTERNATIONAL_SUBJECTS]

/** The listed spelling of a typed subject (ignoring capitals and extra spaces), or null if it isn't listed. */
export function listedSubject(name: string): string | null {
  const key = name.toLowerCase().split(/\s+/).filter(Boolean).join(' ')
  return SUBJECTS.find((s) => s.toLowerCase() === key) ?? null
}

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

/** "Monday 15:00–16:00" */
export function slotText(slot: WeeklyTime): string {
  return `${DAYS[slot.day_of_week]} ${formatTime(slot.start_time)}–${formatTime(slot.end_time)}`
}

/** An ISO timestamp in Nigerian time: "Wed 15 Oct, 15:00". */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Lagos',
  })
}

/** 0.08 -> "8%" */
export function formatPercent(rate: number): string {
  return `${Math.round(rate * 10000) / 100}%`
}

export const BILLING_PERIODS: { value: BillingPeriod; label: string; hint: string }[] = [
  { value: 'daily', label: 'Daily', hint: 'Pay for each day of lessons' },
  { value: 'weekly', label: 'Weekly', hint: 'Pay for a week of lessons at a time' },
  { value: 'monthly', label: 'Monthly', hint: 'Pay for a month of lessons at a time' },
]

export const BOOKING_STATUS_LABEL: Record<BookingStatus, string> = {
  requested: 'Waiting for tutor', accepted: 'Awaiting payment', active: 'Active', paused: 'Paused (unpaid)',
  ended: 'Ended', declined: 'Declined', expired: 'Expired', released: 'Released (unpaid)', cancelled: 'Cancelled',
}

export const PERIOD_STATUS_LABEL: Record<PeriodStatus, string> = {
  due: 'To pay', paid: 'Paid', missed: 'Missed', expired: 'Expired', void: 'Cancelled',
}

export const LESSON_STATUS_LABEL: Record<LessonStatus, string> = {
  confirmed: 'Confirmed', reported: 'Reported', completed: 'Completed', disputed: 'Under review',
  flagged: 'Report missing', refunded: 'Refunded', cancelled: 'Cancelled',
}

export const EARNING_STATUS_LABEL: Record<EarningStatus, string> = {
  pending: 'Upcoming', on_hold: 'On hold', payable: 'To be paid', paid: 'Paid', void: 'Not paid',
}

export const TRANSFER_STATUS_LABEL: Record<TransferStatus, string> = {
  pending: 'Requested', processing: 'Sending', paid: 'Sent', failed: 'Failed', rejected: 'Rejected',
}

export const REFUND_STATUS_LABEL: Record<RefundStatus, string> = {
  pending: 'Waiting for approval', approved: 'Refunded', rejected: 'Rejected',
}

export const ISSUE_KINDS: { value: Exclude<IssueKind, 'no_report'>; label: string }[] = [
  { value: 'tutor_absent', label: "Tutor didn't come" },
  { value: 'late_or_left_early', label: 'Tutor was late or left early' },
  { value: 'agreement_broken', label: 'The agreement was broken' },
  { value: 'other', label: 'Something else' },
]

export const ISSUE_KIND_LABEL: Record<IssueKind, string> = {
  ...Object.fromEntries(ISSUE_KINDS.map((k) => [k.value, k.label])) as Record<Exclude<IssueKind, 'no_report'>, string>,
  no_report: 'Tutor did not report the lesson',
}

export const FEEDBACK_KINDS: { value: FeedbackKind; label: string; hint: string }[] = [
  { value: 'problem', label: 'A problem', hint: 'Something is wrong or not working' },
  { value: 'suggestion', label: 'A suggestion', hint: 'An idea to make TutorLink better' },
  { value: 'question', label: 'A question', hint: 'Something you want to know' },
  { value: 'praise', label: 'Praise', hint: 'Something you liked' },
]

export const FEEDBACK_KIND_LABEL: Record<FeedbackKind, string> = {
  problem: 'Problem', suggestion: 'Suggestion', question: 'Question', praise: 'Praise',
}

export const VETTING_STATUS_LABEL: Record<VettingStatus, string> = {
  pending: 'Under review', approved: 'Approved', rejected: 'Not approved',
}

/** What the parent agrees to before online lessons (the backend stores it with the time). */
export const RECORDING_CONSENT = 'Lessons will be recorded and kept for review.'

export const JOB_STATUS_LABEL: Record<JobStatus, string> = {
  pending: 'Waiting for review', rejected: 'Not approved',
  open: 'Open', ongoing: 'Tutor chosen', completed: 'Completed', closed: 'Closed',
}

export const APPLICATION_STATUS_LABEL: Record<ApplicationStatus, string> = {
  applied: 'Applied', withdrawn: 'Withdrawn', chosen: 'Chosen',
}

export const CERTIFICATES: CertificateType[] = ['WAEC', 'NECO', 'NABTEB', 'NCE', 'Degree', 'PGDE', 'TRCN', 'Other']

/** WAEC and NECO results are confirmed on the exam body's site with the tutor's result-checker PIN (spec 4 R4.2). */
export const CHECKER_CERTIFICATES: CertificateType[] = ['WAEC', 'NECO']

export const CERTIFICATE_STATUS_LABEL: Record<CertificateStatus, string> = {
  pending: 'Waiting for review', verified: 'Verified', rejected: 'Not accepted',
}
