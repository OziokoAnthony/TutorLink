// All TypeScript types for the API. Money and rates arrive from the backend as decimal strings
// ("5000.00"); the lib/ functions convert them to numbers, so pages always get numbers.

export type Role = 'parent' | 'tutor' | 'admin'
export type VettingStatus = 'pending' | 'approved' | 'rejected'
export type Level = 'primary' | 'junior_secondary' | 'senior_secondary' | 'international'
export type LessonMode = 'online' | 'offline'
export type BillingPeriod = 'daily' | 'weekly' | 'monthly'
export type BookingStatus =
  | 'requested' | 'accepted' | 'active' | 'paused' | 'ended' | 'declined' | 'expired' | 'released' | 'cancelled'
export type PeriodStatus = 'due' | 'paid' | 'missed' | 'expired' | 'void'
export type LessonStatus = 'confirmed' | 'reported' | 'completed' | 'disputed' | 'flagged' | 'refunded' | 'cancelled'
export type EarningStatus = 'pending' | 'on_hold' | 'payable' | 'paid' | 'void'
export type IssueKind = 'tutor_absent' | 'late_or_left_early' | 'agreement_broken' | 'other' | 'no_report'
export type IssueResolution = 'refund' | 'reschedule' | 'reject'
export type TransferStatus = 'pending' | 'processing' | 'paid' | 'failed' | 'rejected'
export type RefundStatus = 'pending' | 'approved' | 'rejected'
/** pending: waiting for an admin's review; rejected: not approved (see review_note). */
export type JobStatus = 'pending' | 'rejected' | 'open' | 'ongoing' | 'completed' | 'closed'
export type ApplicationStatus = 'applied' | 'withdrawn' | 'chosen'
export type CertificateType = 'WAEC' | 'NECO' | 'NABTEB' | 'NCE' | 'Degree' | 'PGDE' | 'TRCN' | 'Other'
export type EntryKind = 'deposit' | 'period_payment' | 'refund' | 'withdrawal' | 'withdrawal_reversal'

/** A weekly time range: 0 = Monday ... 6 = Sunday, times as "HH:MM:SS" (or "HH:MM" when sent). */
export interface WeeklyTime {
  day_of_week: number
  start_time: string
  end_time: string
}

// ---------- People ----------

export interface ParentProfile {
  id: string
  user_id: string
  full_name: string
  phone?: string
  address?: string
}

/** Something a tutor teaches: subjects at one level, when, and one price per lesson. */
export interface Offer {
  id: string
  subjects: string[]
  level: Level
  windows: WeeklyTime[]
  price: number
}

export interface TutorProfile {
  id: string
  user_id: string
  full_name: string
  // Only on the tutor's own profile and admin views; the public listing has full_name only.
  first_name?: string
  middle_name?: string | null
  surname?: string
  phone?: string
  bio?: string
  area: string
  photo_url: string | null
  vetting_status: VettingStatus
  vetting_note?: string
  // Tutor's own profile and admin views only (spec 4 R3): when the NIN was verified, which locks the
  // name, and the latest NIN check.
  nin_verified_at?: string | null
  nin_check?: NinCheck | null
  // Public listing and profile only: the badges (spec 4 R4.4).
  nin_verified?: boolean
  verified_certificates?: CertificateType[]
  offers: Offer[]
  price_from: number | null
  average_rating: number | null
  rating_count: number
}

/** A question in an attempt (spec 4 R5). Never carries the correct answer or an explanation. */
export interface ExamQuestion {
  position: number
  text: string
  options: string[]
  /** 0-3, saved as the tutor answers */
  chosen_index: number | null
}

export interface ExamAttempt {
  id: string
  started_at: string
  /** 30 minutes after the start, on the server clock */
  deadline: string
  questions: ExamQuestion[]
}

/** After submitting: the score and pass/fail only, never which answers were right. */
export interface ExamResult {
  id: string
  started_at: string
  submitted_at: string
  score: number
  total: number
  passed: boolean
  seconds_taken: number
}

export interface ExamStatus {
  passed: boolean
  open_attempt: ExamAttempt | null
  /** before the 24-hour lock */
  attempts_left: number
  locked_until: string | null
  /** newest first */
  attempts: ExamResult[]
  pass_mark: number
  total: number
  minutes: number
}

export interface AdminExamAttempt extends ExamResult {
  tutor_id: string
  tutor_name: string
}

export interface AdminExamQuestion {
  id: string
  subject: string | null
  level: Level | null
  text: string
  options: string[]
  correct_index: number
  explanation: string
  model: string
  retired_at: string | null
  created_at: string
}

/** Active bank questions for one tag against its target (general: subject null). */
export interface ExamBankLevel {
  subject: string | null
  level: Level | null
  active: number
  target: number
}

export type CertificateStatus = 'pending' | 'verified' | 'rejected'

/** A tutor's certificate (spec 4 R4). The checker PIN never comes back, only whether one is held. */
export interface Certificate {
  id: string
  type: CertificateType
  institution: string
  year: number
  file_name: string
  /** Short-lived link to the private file */
  file_url: string
  exam_number: string | null
  exam_year: number | null
  has_checker_pin: boolean
  status: CertificateStatus
  review_note: string | null
  reviewed_at: string | null
  created_at: string
}

/** What the admin reviews: the certificate next to the tutor's NIN-verified name, and the PIN while held. */
export interface AdminCertificate extends Certificate {
  tutor_id: string
  tutor_first_name: string
  tutor_middle_name: string | null
  tutor_surname: string
  tutor_nin_verified: boolean
  checker_pin: string | null
}

/** One NIN check with Dojah (spec 4 R3). Never includes the name on the NIN record. */
export interface NinCheck {
  verified: boolean
  nin_last4: string
  nin_found: boolean
  /** null when the NIN wasn't found */
  name_matches: boolean | null
  selfie_matches: boolean | null
  checked_at: string
}

export interface NinResult extends NinCheck {
  message: string
  attempts_left: number
}

export type OnboardingStepKey = 'profile' | 'nin' | 'certificates' | 'quiz' | 'review'

export interface OnboardingStep {
  key: OnboardingStepKey
  done: boolean
  todo: string[]
}

/** The tutor's checklist (spec 4 R2.1). */
export interface Onboarding {
  steps: OnboardingStep[]
  vetting_status: VettingStatus
  nin_attempts_left: number
  nin_retry_at: string | null
}

export interface UserMe {
  id: string
  /** Personal email: notifications go here. Parents and admins log in with it. */
  email: string
  role: Role
  photo_url: string | null
  profile: ParentProfile | TutorProfile | null
  // Parents only: tutors they've had a completed lesson with but haven't rated yet
  tutors_to_rate: TutorToRate[]
}

export interface TutorToRate {
  tutor_id: string
  full_name: string
}

export interface Review {
  rating: number
  comment?: string
  parent_first_name: string
  created_at: string
  updated_at: string
}

export interface TutorFiltersValue {
  subject?: string
  level?: Level
  area?: string
  sort?: 'name' | 'rating' | 'price'
}

export interface TutorAvailability {
  in_session_now: boolean
  busy: WeeklyTime[]
  free: WeeklyTime[]
}

// ---------- Bookings ----------

export interface Period {
  id: string
  starts_on: string
  ends_on: string
  lesson_count: number
  amount: number
  due_at: string
  status: PeriodStatus
  paid_at: string | null
}

/** One shape for all three readers; fields a reader may not see are simply absent. */
export interface Booking {
  id: string
  parent_id: string
  tutor_id: string
  job_id: string | null // set when the booking came from a job post
  subjects: string[]
  level: Level
  mode: LessonMode
  billing_period: BillingPeriod
  start_date: string
  end_date: string | null
  price: number
  child_strengths: string
  child_weaknesses: string
  status: BookingStatus
  slots: WeeklyTime[]
  created_at: string
  responded_at: string | null
  closed_at: string | null
  close_note: string | null
  parent_name: string | null
  tutor_name: string | null
  parent_photo_url: string | null
  tutor_photo_url: string | null
  recording_consent_at: string | null // online bookings: when the parent agreed to recording
  // Online: the tutor's link; the parent gets it once the first period is paid
  meeting_link?: string | null
  // Parent (and admin)
  parent_price_per_lesson?: number
  periods?: Period[]
  // Tutor (and admin)
  tutor_fee_rate?: number
  tutor_earning_per_lesson?: number
  parent_address?: string | null // offline, once the first period is paid
  // Admin only
  parent_fee_rate?: number
  platform_margin_per_lesson?: number
}

export interface BookingInput {
  tutor_id: string
  offer_id: string
  subjects: string[]
  slots: WeeklyTime[]
  start_date: string
  end_date: string | null
  billing_period: BillingPeriod
  mode: LessonMode
  recording_consent: boolean // required for online lessons
  child_strengths: string
  child_weaknesses: string
}

// ---------- Lessons ----------

export interface Issue {
  id: string
  lesson_id: string
  kind: IssueKind
  description: string | null
  raised_automatically: boolean
  resolution: IssueResolution | null
  resolution_note: string | null
  resolved_at: string | null
  created_at: string
}

export interface Lesson {
  id: string
  booking_id: string
  parent_id: string
  tutor_id: string
  lesson_date: string
  start_time: string
  end_time: string
  starts_at: string
  ends_at: string
  status: LessonStatus
  topic_covered: string | null
  homework: string | null
  reported_at: string | null
  problem_window_ends_at: string | null
  price: number
  subjects: string[]
  level: Level | null
  mode: LessonMode | null
  parent_name: string | null
  tutor_name: string | null
  issue: Issue | null
  recording_required: boolean // online: the report needs a recording
  has_recording: boolean
  parent_price?: number
  tutor_earning?: number
  earning_status?: EarningStatus
  payout_due_at?: string
}

// ---------- Money ----------

export interface WalletEntry {
  id: string
  kind: EntryKind
  amount: number
  description: string
  created_at: string
}

export interface VirtualAccount {
  account_number: string
  account_name: string
  bank_name: string
}

export interface Wallet {
  balance: number
  virtual_account: VirtualAccount | null
  amount_due: number
  entries: WalletEntry[]
}

export interface Bank {
  name: string
  code: string
}

export interface Withdrawal {
  id: string
  amount: number
  bank_name: string
  account_number: string
  account_name: string
  status: TransferStatus
  note: string | null
  created_at: string
  processed_at: string | null
  // Admin
  parent_id?: string
  parent_name?: string | null
  bank_code?: string
  reference?: string
}

export interface Refund {
  id: string
  parent_id: string
  booking_id: string
  reason: 'cancellation' | 'lesson_issue'
  lesson_count: number
  amount: number
  status: RefundStatus
  note: string | null
  decided_at: string | null
  created_at: string
  parent_name: string | null
}

export interface EarningsSummary {
  pending: number
  on_hold: number
  payable: number
  paid: number
}

export interface BankAccountTutorView {
  bank_name: string
  account_last4: string
  account_name: string
  name_matches: boolean
  approved_for_payouts: boolean
}

export interface BankAccountAdminView {
  bank_code: string
  bank_name: string
  account_number: string
  account_name: string
  name_matches: boolean
  override_note: string | null
}

export interface PayoutDue {
  tutor_id: string
  tutor_name: string | null
  amount: number
  lesson_count: number
  due_at: string
  overdue: boolean
  bank_account: BankAccountAdminView | null
  can_send: boolean
}

export interface Payout {
  id: string
  tutor_id: string
  tutor_name: string | null
  amount: number
  lesson_count: number
  method: 'paystack' | 'manual'
  status: TransferStatus
  reference: string
  note: string | null
  created_at: string
  paid_at: string | null
}

export interface Fees {
  parent_fee_rate: number
  tutor_fee_rate: number
  updated_at: string
}

export interface ReceiptLine {
  description: string
  amount: number
}

/** A parent's receipt: what they paid or got back. Never shows the fee. */
export interface ParentReceipt {
  receipt_number: string
  issued_at: string
  parent_name: string | null
  parent_email: string
  kind: EntryKind
  title: string
  lines: ReceiptLine[]
  total: number
  balance_after: number
}

export interface PayoutReceiptLine {
  lesson_date: string
  subjects: string[]
  parent_first_name: string
  price: number
  tutor_fee: number
  earning: number
}

/** A tutor's payout receipt: agreed price, TutorLink's fee and earning, lesson by lesson. */
export interface PayoutReceipt {
  receipt_number: string
  issued_at: string
  tutor_name: string | null
  tutor_email: string
  method: Payout['method']
  status: TransferStatus
  tutor_fee_rate: number | null
  bank: string | null
  lines: PayoutReceiptLine[]
  total_price: number
  total_fee: number
  total: number
}

// ---------- Notifications ----------

export interface AppNotification {
  id: string
  title: string
  body: string
  link: string | null
  read_at: string | null
  created_at: string
}

export interface NotificationList {
  unread_count: number
  items: AppNotification[]
}

// ---------- Feedback and the help assistant (spec 6) ----------

export type FeedbackKind = 'problem' | 'suggestion' | 'praise' | 'question'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface Feedback {
  id: string
  kind: FeedbackKind
  message: string
  transcript: ChatMessage[] | null
  reply: string | null
  replied_at: string | null
  created_at: string
  // Admin only
  user_id?: string
  user_name?: string | null
  user_email?: string
  user_role?: Role
}

// ---------- Job posts (spec 2) ----------

/** What a parent sends to post or edit a job. */
export interface JobInput {
  subjects: string[]
  level: Level
  mode: LessonMode
  area: string | null
  slots: WeeklyTime[]
  start_date: string
  end_date: string | null
  billing_period: BillingPeriod
  qualifications: string
  min_certificate: CertificateType | null
  other_requirements: string | null
  price: number
  child_strengths: string
  child_weaknesses: string
  recording_consent: boolean // required for online lessons
}

export interface MyApplication {
  id: string
  job_id: string
  note: string | null
  status: ApplicationStatus
  withdrawn_reason: string | null
  created_at: string
}

/** One shape for both readers; fields a reader may not see are simply absent. */
export interface Job extends JobInput {
  id: string
  status: JobStatus
  created_at: string
  // Parent
  parent_price_per_lesson?: number
  booking_id?: string | null
  applicant_count?: number
  review_note?: string | null // why an admin didn't approve it
  // Admin
  parent_id?: string
  parent_name?: string | null
  reviewed_at?: string | null
  updated_at?: string
  // Tutor
  tutor_fee_rate?: number
  tutor_earning_per_lesson?: number
  parent_first_name?: string
  parent_photo_url?: string | null
  my_application?: MyApplication | null
}

/** A tutor who applied, as the parent sees them. */
export interface Applicant {
  id: string
  tutor_id: string
  tutor_name: string | null
  tutor_photo_url: string | null
  average_rating: number | null
  rating_count: number
  note: string | null
  status: ApplicationStatus
  created_at: string
}

export interface JobFiltersValue {
  subject?: string
  level?: Level
  mode?: LessonMode
  area?: string
}
