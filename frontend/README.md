# TutorLink Frontend

The Next.js web app for TutorLink, where Nigerian parents find vetted home tutors, book weekly
lessons and pay ahead by bank transfer, and TutorLink pays tutors after the lessons. It talks to the
TutorLink backend in [`../backend`](../backend) (FastAPI) at `NEXT_PUBLIC_API_URL`.

Stack: Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind CSS 3 · shadcn/ui · React Hook Form + Zod · Axios.
What it does is specified in [`../specs/`](../specs/); `CLAUDE.md` covers how the code is organised.

## Run it

```bash
# 1. Backend running (from ../backend):  docker compose up -d
# 2. Frontend:
cp .env.local.example .env.local
npm install
npm run dev          # http://localhost:3000
```

The backend's `FRONTEND_URL` must match this app's address (default `http://localhost:3000`) for CORS
and the links in notification emails.

## Accounts

- **Parents and tutors** register at `/register`.
- **Admins** are created on the backend:
  `docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng`

## Where things live

| Path | What |
|---|---|
| `app/` | Pages: `dashboard/parent/`, `dashboard/tutor/`, `admin/`, `receipts/` |
| `lib/` | **All** API calls. Converts backend responses to the types in `types/index.ts` (e.g. money strings → numbers). Pages never call Axios directly. |
| `middleware.ts` | `/dashboard/*`, `/admin/*` and `/receipts/*` require the `tutorlink_token` cookie. Each area also requires the right role, which is read from the JWT; the backend still checks every request. |
| `hooks/useAuth.ts` | Current user (`/auth/me`), login (redirects by role), logout |

## Payments in development

Parents pay by bank transfer into their own Paystack account number; there is no card checkout.
To try it end to end you need Paystack **test** keys in the backend `.env`, with Dedicated Virtual
Accounts and Transfers enabled, and the webhook must reach the backend (e.g. `ngrok http 8000`,
with the webhook URL set in the Paystack dashboard). Without that, parents can't get an account
number and balances don't change; everything else (offers, requests, accepting) still works.
