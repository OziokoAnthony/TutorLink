# TutorLink Frontend

The Next.js web app for TutorLink, where Nigerian parents find vetted home tutors, book weekly
lessons, and pay monthly for confirmed lessons only. It talks to the
TutorLink backend in [`../backend`](../backend) (FastAPI) at `NEXT_PUBLIC_API_URL`.

Stack: Next.js 14 (App Router) · TypeScript (strict) · Tailwind CSS 3 · shadcn/ui · React Hook Form + Zod · Axios.
See `CLAUDE.md` for the full spec.

## Run it

```bash
# 1. Backend running (from ../backend):  docker compose up -d
# 2. Frontend:
cp .env.local.example .env.local
npm install
npm run dev          # http://localhost:3000
```

The backend's `FRONTEND_URL` must match this app's address (default `http://localhost:3000`) for CORS
and the Paystack return URL.

## Accounts

- **Parents and tutors** register at `/register`.
- **Admins** are created on the backend:
  `docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng`

## Where things live

| Path | What |
|---|---|
| `app/` | Pages (see `CLAUDE.md` → *Pages*) |
| `lib/` | **All** API calls. Converts backend responses to the types in `types/index.ts` (e.g. money strings → numbers). Pages never call Axios directly. |
| `middleware.ts` | `/dashboard/*` and `/admin/*` require the `tutorlink_token` cookie. Each area also requires the right role, which is read from the JWT; the backend still checks every request. |
| `hooks/useAuth.ts` | Current user (`/auth/me`), login (redirects by role), logout |

## Additions on top of `CLAUDE.md`

- **Tutor ratings:**
  - Stars and rating count on tutor cards and profiles.
  - "Top rated" sort.
  - Reviews on each tutor's profile.
  - "Rate your tutors" prompts for parents.
- **Log a session:** offers all of the tutor's schedules, today's first, so a lesson can be logged after the day it happened. The date must fall on the schedule's weekday.
- **Failed payments:** an invoice with status `failed` shows "Try again". A paid invoice never shows a pay button.
- **Return from Paystack:** parents come back to `/dashboard/parent/invoices?invoice=<id>`. The page refreshes until the webhook marks the invoice paid.

## Payments in development

Paystack's checkout needs real **test** keys in the backend `.env`. Its webhook must also be able
to reach the backend, e.g. through `ngrok http 8000`, with the webhook URL set in the Paystack
dashboard. Without that, "Pay Now" shows an error and invoices stay `pending`.
