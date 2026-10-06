// All TypeScript types. The interfaces from CLAUDE.md are kept as written; fields the backend
// added later (ratings, names) are appended and marked optional where a response may omit them.

export type Role = 'parent' | 'tutor' | 'admin'
export type VettingStatus = 'pending' | 'approved' | 'rejected'
export type SessionStatus = 'scheduled' | 'logged' | 'confirmed' | 'cancelled'
export type InvoiceStatus = 'pending' | 'paid' | 'failed'
export type Level = 'primary' | 'junior_secondary' | 'senior_secondary'

export interface User {
  id: string
  email: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface ParentProfile {
  id: string
  user_id: string
  full_name: string
  phone?: string
  address?: string
}

export interface TutorSubject {
  id: string
  subject: string
  level: Level
}

export interface TutorProfile {
  id: string
  user_id: string
  full_name: string
  phone?: string
  bio?: string
  area: string
  rate_per_session: number
  vetting_status: VettingStatus
  vetting_note?: string
  subjects: TutorSubject[]
  // Ratings (backend addendum)
  average_rating: number | null
  rating_count: number
}

export interface UserMe {
  id: string
  email: string
  role: Role
  profile: ParentProfile | TutorProfile | null
  // Parents only: tutors they've had a confirmed session with but haven't rated yet
  tutors_to_rate: TutorToRate[]
}

export interface Schedule {
  id: string
  tutor_id: string
  parent_id: string
  day_of_week: number
  start_time: string
  end_time: string
  subject: string
  level: Level
  is_active: boolean
  created_at: string
  tutor_name?: string
  parent_name?: string
}

export interface Session {
  id: string
  schedule_id: string
  session_date: string
  topic_covered?: string
  homework?: string
  status: SessionStatus
  logged_at?: string
  confirmed_at?: string
  // From the session's schedule (backend addendum)
  subject?: string
  level?: Level
  tutor_id?: string
  tutor_name?: string
  parent_name?: string
}

export interface InvoiceItem {
  id: string
  session_id: string
  tutor_id: string
  session_date: string
  amount: number
  commission_amount: number
}

export interface Invoice {
  id: string
  parent_id: string
  billing_month: number
  billing_year: number
  total_sessions: number
  subtotal: number
  commission_rate: number
  commission_amount: number
  total_amount: number
  status: InvoiceStatus
  paid_at?: string
  items: InvoiceItem[]
  parent_name?: string
}

// ---------- Added for features beyond the original type list ----------

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
  sort?: 'name' | 'rating'
}

export interface GenerateInvoicesResult {
  created: number
  skipped_existing: number
  parents_without_sessions: number
  invoices: Invoice[]
}
