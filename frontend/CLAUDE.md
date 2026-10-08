# TutorLink Frontend — CLAUDE.md

TutorLink is a home tutoring marketplace for Nigerian parents. This folder is the Next.js web app;
it calls the FastAPI backend in `../backend/` at `NEXT_PUBLIC_API_URL` (`http://localhost:8000/v1`).
`README.md` covers running it.

## What to build: the specs

The product is specified in `../specs/`, one approved spec per feature, built in order:

1. `feature-1-bookings-and-payments.md`: offers, booking requests, prepaid bank-transfer payments, hidden fees, lessons, problems and refunds, tutor payouts. **Built.**
2. `feature-2-job-posts.md`: parents post jobs with their own price, approved tutors apply, choosing one books them. **Built.**
3. `feature-3-online-lessons.md`
4. `feature-4-tutor-onboarding.md`
5. `feature-5-international.md` (draft: location, NGN/USD, job visibility by country)

Read the spec before changing a feature it covers, and check the backend's request and response
models (`../backend/app/domains/*/models.py`) or `/docs` for the exact API shape.

## Stack

Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS · shadcn/ui (`components/ui/`) ·
React Hook Form + Zod · Axios · sonner toasts · lucide icons.

## Where things live

- `app/`: pages. Parent pages under `dashboard/parent/`, tutor pages under `dashboard/tutor/`,
  admin pages under `admin/`, printable receipts under `receipts/`.
- `lib/`: every API call, one module per backend domain (`bookings`, `lessons`, `wallet`,
  `payouts`, `tutors`, `notifications`, `auth`). Pages import these; Axios stays inside `lib/`.
- `lib/format.ts`: all display text for enums (status labels, issue kinds, billing periods),
  money, dates and times. `components/shared/StatusBadge.tsx`: the coloured badge for each status.
- `types/index.ts`: every API type.
- `components/layout/Sidebar.tsx`: `LINKS`, the one list of each role's pages; the navbar menus
  read it too.
- `middleware.ts`: `/dashboard`, `/admin` and `/receipts` need the `tutorlink_token` cookie, and
  each area its role (read from the JWT for routing; the backend checks every request).

## Conventions

- **Money arrives as decimal strings** (`"5000.00"`). Each `lib/` function converts the money and
  rate fields with `numbers()` from `lib/convert.ts`, so pages always get numbers. Rates are
  fractions (`0.08`); show them with `formatPercent`, money with `formatNaira`.
- **Dates.** `YYYY-MM-DD` values go through `parseDate`/`formatDate` (no timezone shift). ISO
  timestamps go through `formatDateTime`, which shows Nigerian time.
- **Who sees what (spec 1, R1).** The backend returns a different shape of the same booking or
  lesson to the parent, the tutor and the admin; fields a reader may not see are optional in the
  type and absent from the response. Show only what the response carries: a parent page shows the
  parent's own amounts and P, never a fee rate or tutor earning; a tutor page shows P, their fee and
  earning, never the parent's total.
- **Loading and errors.** A page holds `null` while loading (`LoadingSpinner`), shows `EmptyState`
  for an empty list, and reports failures with `toast.error(errorMessage(e))`. The backend's
  `detail` text is written for users and shown as is.
- **Dialogs.** `ConfirmDialog` and `NoteDialog` stay open while `onConfirm` runs and close when it
  resolves. On failure, show the toast and rethrow so the dialog stays open.
- **Words.** Users see *lesson*, *booking*, *balance* (their TutorLink balance), *TutorLink's fee*
  and *receipt*, in short plain sentences.

## Guardrails

- Every fee figure on screen comes from the API response for that reader.
- A tutor's full bank account number appears only on admin pages; tutors see bank and last 4 digits.
- `password_hash` never reaches the UI.

## Checking your work

```bash
npm run lint
npm run build      # type-check + lint + production build; the bar for "done"
```

If the build reports missing modules under `.next/types/` for pages that were deleted, the cache is
stale: delete `.next` and build again.
