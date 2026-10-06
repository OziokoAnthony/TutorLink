# TutorLink Frontend — CLAUDE.md
# Read this file before doing anything. Follow every instruction exactly.

---

## WHAT WE ARE BUILDING

TutorLink is a home tutoring platform where Nigerian parents find vetted tutors,
book recurring weekly sessions, and pay monthly — only for confirmed lessons.

This folder is the **frontend only** (Next.js web app). It lives in `frontend/` of the TutorLink
repository; the backend is in `../backend/`.
It communicates with a FastAPI backend at `http://localhost:8000/v1`.

---

## STACK

```
Framework:        Next.js 14 (App Router)
Language:         TypeScript (strict mode)
Styling:          Tailwind CSS
Components:       shadcn/ui
Forms:            React Hook Form + Zod
HTTP client:      Axios (with JWT interceptor)
Auth:             JWT stored in httpOnly cookie (name: tutorlink_token)
Package manager:  npm
```

---

## FOLDER STRUCTURE

```
tutorlink-frontend/
├── app/
│   ├── layout.tsx                    ← Root layout (font, providers, Toaster)
│   ├── page.tsx                      ← Landing page (/)
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx             ← Login form
│   │   └── register/
│   │       └── page.tsx             ← Register (choose parent or tutor)
│   ├── tutors/
│   │   ├── page.tsx                 ← Browse tutors with filters
│   │   └── [id]/
│   │       └── page.tsx             ← Single tutor profile + book button
│   ├── dashboard/
│   │   ├── parent/
│   │   │   ├── page.tsx             ← Parent dashboard overview
│   │   │   ├── schedules/
│   │   │   │   └── page.tsx         ← My recurring schedules
│   │   │   ├── sessions/
│   │   │   │   └── page.tsx         ← Sessions awaiting confirmation
│   │   │   └── invoices/
│   │   │       └── page.tsx         ← My invoices + pay button
│   │   └── tutor/
│   │       ├── page.tsx             ← Tutor dashboard overview
│   │       ├── profile/
│   │       │   └── page.tsx         ← Edit profile + manage subjects
│   │       └── sessions/
│   │           └── page.tsx         ← Log a session
│   └── admin/
│       ├── tutors/
│       │   └── page.tsx             ← Pending tutors — approve/reject
│       └── invoices/
│           └── page.tsx             ← Generate monthly invoices
├── components/
│   ├── ui/                          ← shadcn/ui components (auto-generated)
│   ├── layout/
│   │   ├── Navbar.tsx               ← Top nav with role-based links + logout
│   │   └── Sidebar.tsx              ← Dashboard sidebar (different per role)
│   ├── tutors/
│   │   ├── TutorCard.tsx            ← Card in /tutors grid
│   │   ├── TutorFilters.tsx         ← Subject, level, area filter bar
│   │   └── BookingForm.tsx          ← Book recurring slot modal
│   ├── sessions/
│   │   ├── SessionCard.tsx          ← Session row with confirm button
│   │   └── LogSessionForm.tsx       ← Tutor logs topic + homework
│   ├── invoices/
│   │   └── InvoiceCard.tsx          ← Invoice summary card + pay button
│   └── shared/
│       ├── LoadingSpinner.tsx
│       ├── EmptyState.tsx
│       └── ConfirmDialog.tsx        ← Reusable confirmation modal
├── lib/
│   ├── api.ts                       ← Axios instance + JWT interceptor
│   ├── auth.ts                      ← login(), register(), getMe(), logout()
│   ├── tutors.ts                    ← getTutors(), getTutor(), vetTutor()
│   ├── schedules.ts                 ← createSchedule(), getMySchedules(), cancelSchedule()
│   ├── sessions.ts                  ← logSession(), getMySessions(), confirmSession()
│   └── billing.ts                  ← getMyInvoices(), getInvoice(), payInvoice(), generateInvoices()
├── hooks/
│   ├── useAuth.ts                   ← Current user state, redirect on role
│   └── useToast.ts                  ← Toast notification helper
├── middleware.ts                    ← Protect /dashboard and /admin routes
├── types/
│   └── index.ts                     ← All TypeScript types
├── .env.local.example
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## TYPESCRIPT TYPES (types/index.ts)

```typescript
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
}

export interface UserMe {
  id: string
  email: string
  role: Role
  profile: ParentProfile | TutorProfile | null
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
}
```

---

## API CLIENT SETUP (lib/api.ts)

```typescript
import axios from 'axios'
import Cookies from 'js-cookie'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1',
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = Cookies.get('tutorlink_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('tutorlink_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
```

---

## AUTH FLOW

```
1. User submits login form
2. POST /v1/auth/login → backend returns { access_token, token_type }
3. Store token: Cookies.set('tutorlink_token', access_token, { expires: 1 })
4. Call GET /v1/auth/me to get user role
5. Redirect based on role:
   - parent → /dashboard/parent
   - tutor  → /dashboard/tutor
   - admin  → /admin/tutors
6. On every page load: useAuth() hook reads cookie, fetches /auth/me
7. On logout: Cookies.remove('tutorlink_token') → redirect to /
```

---

## MIDDLEWARE — ROUTE PROTECTION (middleware.ts)

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const token = request.cookies.get('tutorlink_token')
  const { pathname } = request.nextUrl

  const protectedPrefixes = ['/dashboard', '/admin']
  const isProtected = protectedPrefixes.some(p => pathname.startsWith(p))

  if (isProtected && !token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/admin/:path*'],
}
```

---

## PAGES — WHAT EACH ONE MUST DO

### `/` — Landing Page
- Hero: "Find a vetted home tutor. Pay only for lessons that happened."
- Two CTA buttons: "Find a Tutor" → /tutors | "Become a Tutor" → /register
- How it works: 3 steps (Search → Book → Pay confirmed lessons)
- No auth required. Works for everyone.

### `/register` — Registration Page
- Toggle: "I'm a Parent" | "I'm a Tutor"
- Common fields: email, password, full_name, phone
- Parent extra fields: address
- Tutor extra fields: area, rate_per_session (number), bio
- Zod validation on all fields before submit
- On submit: POST /v1/auth/register
- On success: show toast "Account created!" → redirect to /login
- On error 409: show "Email already registered"

### `/login` — Login Page
- Fields: email, password
- On submit: POST /v1/auth/login
- On success: store token cookie → redirect by role
- On error 401: show "Invalid email or password"

### `/tutors` — Browse Tutors
- Filter bar at top: Subject (select), Level (select), Area (text input)
- Grid of TutorCard components below
- TutorCard shows: full_name, area, subjects (badges), rate_per_session, "View Profile" button
- Fetches: GET /v1/tutors?subject=...&level=...&area=...
- No auth required
- Empty state: "No tutors found. Try different filters."

### `/tutors/[id]` — Single Tutor Profile
- Full profile: name, bio, area, subjects+levels (badge list), rate per session
- "Book a Session" button — only visible if user is logged in as parent
- Clicking "Book a Session" opens BookingForm modal
- BookingForm fields: day_of_week (select: Monday–Sunday), start_time, end_time, subject (select from tutor's subjects)
- On submit: POST /v1/schedules
- On 409 error: show "This tutor is already booked at that time. Please choose another slot."
- On success: show "Session booked!" → redirect to /dashboard/parent/schedules

### `/dashboard/parent` — Parent Overview
- Summary cards:
  - "Active Schedules" → count from GET /v1/schedules/me
  - "Sessions to Confirm" → count of sessions with status=logged
  - "Unpaid Invoices" → count of invoices with status=pending
- Quick links to /dashboard/parent/schedules, /sessions, /invoices

### `/dashboard/parent/schedules` — My Schedules
- List of active recurring schedules from GET /v1/schedules/me
- Each row: tutor name, subject, level, day of week, time, "Cancel" button
- Cancel opens ConfirmDialog: "Are you sure you want to cancel this recurring session?"
- On confirm: DELETE /v1/schedules/{id}
- On success: remove from list, show toast "Schedule cancelled"

### `/dashboard/parent/sessions` — Confirm Sessions
- Tabs: "To Confirm" (status=logged) | "Confirmed" | "All"
- Each session card shows: date, tutor name, subject, topic covered, homework, status badge
- "To Confirm" tab has a "Confirm" button on each card
- On confirm: PATCH /v1/sessions/{id}/confirm
- On success: move session to Confirmed tab, show toast "Session confirmed!"
- Empty state for "To Confirm": "All sessions confirmed. Great job!"

### `/dashboard/parent/invoices` — My Invoices
- List of invoices from GET /v1/invoices/me
- Each InvoiceCard shows: month+year, total sessions, total amount, status badge
- Status badges: "Pending" (yellow), "Paid" (green), "Failed" (red)
- "Pay Now" button on pending invoices
- On "Pay Now": POST /v1/invoices/{id}/pay → backend returns { authorization_url }
- Redirect browser to authorization_url (Paystack checkout page)
- When Paystack redirects back → show invoice list, refresh statuses

### `/dashboard/tutor` — Tutor Overview
- Vetting status banner at top:
  - pending: "Your profile is under review. You'll be notified once approved."
  - rejected: "Your application was not approved. [vetting_note]"
  - approved: no banner
- Summary cards: "Sessions This Month", "Upcoming Sessions Today"
- Quick links to /dashboard/tutor/profile and /dashboard/tutor/sessions

### `/dashboard/tutor/profile` — Edit Profile
- Editable form: full_name, phone, bio, area, rate_per_session
- On submit: POST /v1/tutors/profile (create or update)
- Subjects section below form:
  - List of existing subjects with "Remove" button on each
  - "Add Subject" form: subject (text), level (select)
  - Add: POST /v1/tutors/profile/subjects
  - Remove: DELETE /v1/tutors/profile/subjects/{id}
- Vetting status shown as read-only badge (cannot edit)

### `/dashboard/tutor/sessions` — Log a Session
- Select from today's active schedules (GET /v1/schedules/tutor/me filtered to today's day_of_week)
- Fields: session_date (date picker, max=today), topic_covered (textarea), homework (textarea)
- On submit: POST /v1/sessions
- On 409: "You already logged a session for this date."
- On success: show "Session logged! The parent will be notified to confirm." → clear form
- Below form: list of recently logged sessions (last 10)

### `/admin/tutors` — Vet Tutors
- Table of pending tutors from GET /v1/admin/tutors/pending
- Columns: full_name, area, subjects, rate_per_session, bio
- Each row: "Approve" button (green) and "Reject" button (red)
- Approve: PATCH /v1/tutors/{id}/vet with { status: 'approved' }
- Reject: opens modal with textarea for rejection note → PATCH /v1/tutors/{id}/vet with { status: 'rejected', note }
- On action: remove tutor from table, show toast
- Empty state: "No tutors pending review."

### `/admin/invoices` — Generate Invoices
- Month selector (1–12) and Year input
- "Generate Invoices" button
- On submit: POST /v1/invoices/generate with { month, year }
- Show result summary: "X invoices generated. Y parents had no confirmed sessions."
- Below: table showing generated invoices (parent name, sessions count, amount)

---

## COMPONENT DETAILS

### Navbar.tsx
- Logo "TutorLink" on left → links to /
- If NOT logged in: "Browse Tutors", "Login", "Register" links
- If logged in as parent: "Find Tutors", "Dashboard" dropdown → Schedules, Sessions, Invoices
- If logged in as tutor: "Dashboard" dropdown → Profile, Log Session
- If logged in as admin: "Vet Tutors", "Invoices"
- "Logout" button always shown when logged in

### TutorCard.tsx
```
┌─────────────────────────────────┐
│  [Avatar placeholder]           │
│  John Adebayo                   │
│  Lagos Island                   │
│  Mathematics • Primary          │
│  Chemistry • Senior Secondary   │
│  ₦3,500 per session             │
│  [View Profile]                 │
└─────────────────────────────────┘
```

### BookingForm.tsx (Modal)
- Day of week: select (Monday, Tuesday, ..., Sunday)
- Start time: time input
- End time: time input
- Subject: select from tutor's subjects
- Zod validation: end_time must be after start_time
- Submit calls POST /v1/schedules
- Show 409 clash error inline under the time fields

### SessionCard.tsx
```
┌─────────────────────────────────────────┐
│  Tuesday, 15 Oct 2025    [Logged badge]  │
│  Mathematics — Tutor: John Adebayo      │
│  Topic: Algebra — Linear Equations      │
│  Homework: Exercises 3.1 to 3.5         │
│                          [Confirm] btn  │
└─────────────────────────────────────────┘
```

### InvoiceCard.tsx
```
┌────────────────────────────────────────┐
│  October 2025              [Pending]   │
│  4 confirmed sessions                  │
│  Total: ₦14,000                        │
│                         [Pay Now] btn  │
└────────────────────────────────────────┘
```

---

## ENVIRONMENT VARIABLES (.env.local.example)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/v1
NEXT_PUBLIC_PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## PACKAGES TO INSTALL

```bash
npx create-next-app@latest tutorlink-frontend --typescript --tailwind --app --src-dir=no --import-alias="@/*"

# Then install:
npm install axios js-cookie react-hook-form zod @hookform/resolvers
npm install @types/js-cookie

# shadcn/ui setup:
npx shadcn@latest init
# Install components as needed:
npx shadcn@latest add button card input label select textarea badge dialog toast tabs
```

---

## HOW FRONTEND CALLS BACKEND

```
User action on page
    ↓
lib function (e.g. lib/schedules.ts → createSchedule())
    ↓
api.ts (Axios instance) — adds Authorization: Bearer <token>
    ↓
FastAPI backend at http://localhost:8000/v1/...
    ↓
JSON response
    ↓
Update page state / show toast / redirect
```

All API functions live in `lib/`. Pages import from `lib/`, never call Axios directly.

---

## BUILD ORDER

```
Step 1:  Scaffold project (create-next-app, install packages, shadcn/ui init)
Step 2:  Set up types/index.ts (all TypeScript types)
Step 3:  Set up lib/api.ts (Axios + interceptors)
Step 4:  Set up middleware.ts (route protection)
Step 5:  Set up useAuth.ts hook
Step 6:  Build Navbar.tsx

Step 7:  Landing page (/)
Step 8:  /register and /login pages
         Test: register as parent → login → redirected to /dashboard/parent

Step 9:  /tutors browse page + TutorCard + TutorFilters
Step 10: /tutors/[id] profile page + BookingForm modal
         Test: book a slot → redirected to schedules page

Step 11: /dashboard/parent/schedules
Step 12: /dashboard/parent/sessions (with confirm button)
Step 13: /dashboard/parent/invoices (with pay button)
Step 14: /dashboard/parent overview

Step 15: /dashboard/tutor/profile
Step 16: /dashboard/tutor/sessions (log form)
Step 17: /dashboard/tutor overview

Step 18: /admin/tutors (vet pending tutors)
Step 19: /admin/invoices (generate monthly)
```

---

## FULL USER JOURNEY — TEST THIS END TO END

```
1. Register as parent (John, john@email.com)
2. Register as tutor (Amara, amara@email.com, area=Lekki, rate=3500)
3. Login as admin → go to /admin/tutors → approve Amara
4. Login as Amara (tutor) → go to /dashboard/tutor/profile → add subject: Mathematics, Senior Secondary
5. Login as John (parent) → browse /tutors → find Amara → book Tuesday 3pm-4pm Mathematics
6. Login as Amara → go to /dashboard/tutor/sessions → log a session for John's Tuesday slot
   (topic: Algebra, homework: Exercises 3.1)
7. Login as John → go to /dashboard/parent/sessions → see session awaiting confirmation → confirm it
8. Login as admin → go to /admin/invoices → generate for current month
9. Login as John → go to /dashboard/parent/invoices → see invoice → click Pay Now → Paystack checkout
10. Complete payment in Paystack test mode → return to app → invoice shows "Paid"
```

---

## NEVER ALLOWED

- Dashboard pages accessible without JWT cookie ❌
- Admin pages accessible by parent or tutor ❌
- password_hash rendered anywhere ❌
- Hardcoded API URL (must use NEXT_PUBLIC_API_URL env var) ❌
- Direct Axios calls in page components (must go through lib/) ❌
- "Pay Now" button on an already-paid invoice ❌
- Unapproved tutor shown on /tutors page ❌
