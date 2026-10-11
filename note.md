# TutorLink: The Complete Project Notes

> Read this from top to bottom once. After that, use it as a reference: every section stands on its own.
> Each technical idea is explained twice: first **in simple words** (like to a child), then **the engineering
> version** (like to a junior engineer).

---

## Table of contents

1. [What is TutorLink?](#1-what-is-tutorlink)
2. [The people who use it (roles)](#2-the-people-who-use-it-roles)
3. [How the project was planned: specs](#3-how-the-project-was-planned-specs)
4. [Every feature, explained](#4-every-feature-explained)
5. [The money maths](#5-the-money-maths)
6. [The big picture: how the pieces talk](#6-the-big-picture-how-the-pieces-talk)
7. [Folder structure](#7-folder-structure)
8. [Backend: stack and why](#8-backend-stack-and-why)
9. [Backend: how the code is organised](#9-backend-how-the-code-is-organised)
10. [Database: every table](#10-database-every-table)
11. [Every API endpoint](#11-every-api-endpoint)
12. [Background jobs (the robot that runs every minute)](#12-background-jobs)
13. [Outside services we use](#13-outside-services-we-use)
14. [Frontend: stack and why](#14-frontend-stack-and-why)
15. [Frontend: every page (route)](#15-frontend-every-page-route)
16. [Frontend: every component, hook and lib file](#16-frontend-every-component-hook-and-lib-file)
17. [Security: every protection and why](#17-security-every-protection-and-why)
18. [Testing](#18-testing)
19. [Running it on your computer](#19-running-it-on-your-computer)
20. [Deployment (Vercel + Render)](#20-deployment-vercel--render)
21. [Glossary](#21-glossary)
22. [Questions a senior engineer will ask (with answers)](#22-questions-a-senior-engineer-will-ask-with-answers)
23. [Honest limits and what I'd improve next](#23-honest-limits-and-what-id-improve-next)

---

## 1. What is TutorLink?

**In simple words:** TutorLink is a website where Nigerian parents find a good home teacher (a tutor) for their
child. The parent picks a tutor, the tutor says "yes", the parent pays **before** the lessons by sending money
from their bank, and TutorLink pays the tutor **after** the lessons happen. TutorLink keeps a small fee from
both sides.

**The engineering version:** a two-sided marketplace (parents ↔ tutors) with:

- tutor discovery and vetting (NIN identity check, certificates, an AI-generated qualifying exam);
- recurring weekly bookings with prepaid billing periods (daily, weekly or monthly);
- bank-transfer-only payments through Paystack Dedicated Virtual Accounts (each parent gets their own account number);
- a ledger-based wallet (the "balance");
- lesson reports, recordings for online lessons, problem reports and refunds;
- admin-driven tutor payouts through Paystack Transfers;
- job posts (parents post what they need, tutors apply);
- feedback and an AI help assistant;
- admin-managed subjects and legal pages.

**Why it exists (the business problem):**
- Parents struggle to find tutors they can trust → we vet tutors hard (NIN + certificates + exam).
- Parents worry about paying for lessons that never happen → money is held by TutorLink, tutors must report every
  lesson (with a recording if online), parents can complain within 24 hours, and the tutor is paid only after that.
- Tutors worry about not being paid → parents pay *before* lessons.

---

## 2. The people who use it (roles)

There are exactly **three roles**, stored in `users.role`:

| Role | Who | What they can do |
|---|---|---|
| **parent** | A mum/dad/guardian | Browse tutors, request bookings, post jobs, pay, see lessons, report problems, rate tutors, withdraw balance, send feedback |
| **tutor** | A teacher | Set offers (subjects + times + price), go through onboarding, accept/decline bookings, apply to jobs, report lessons, upload recordings, see earnings |
| **admin** | TutorLink staff | Approve tutors, check certificates, approve jobs, resolve problems, approve refunds, pay tutors, handle withdrawals, set fees, manage subjects and legal pages, answer feedback |

- Nobody can sign up as an admin. Admins are created with a command-line script (`app/scripts/create_admin.py`).
- One email = one account = one role. The same Google email can't be a parent and a tutor (409 error).

---

## 3. How the project was planned: specs

**In simple words:** before building anything, we wrote down exactly what each feature must do, like a recipe.
Then we built it, and wrote tests that check every line of the recipe.

**The engineering version:** the project is **spec-driven**. Every feature has a spec in `specs/`:

| # | Spec | Status |
|---|---|---|
| 1 | `feature-1-bookings-and-payments.md`: offers, bookings, prepaid payments, hidden fees, lessons, refunds, payouts | Built |
| 2 | `feature-2-job-posts.md`: parents post jobs, tutors apply | Built |
| 3 | `feature-3-online-lessons.md`: online/offline lessons, meeting links, recordings | Built |
| 4 | `feature-4-tutor-onboarding.md`: email/Google sign-up, password reset, photos, NIN, certificates, exam | Built |
| 5 | `feature-5-international.md`: other countries, US dollars | **Draft, not built** |
| 6 | `feature-6-feedback-and-help.md`: feedback + Claude help chat | Built |
| 7 | `feature-7-admin-content.md`: admins manage subjects and legal pages | Built |

Every spec has the same shape:

1. **Why**: the business problem.
2. **Terms**: words with exact meanings (e.g. "P" = agreed price per lesson).
3. **Requirements** with IDs like **R2.6** ("spec 1, requirement 2, point 6"). These IDs are quoted in code
   comments and tests, so you can trace any rule from the spec to the code to the test.
4. **Non-goals**: what we decided *not* to build (e.g. card payments).
5. **Acceptance criteria**: a checklist; each item became an automated test.
6. **Assumptions**.

**Build order:** spec 1 first (everything else depends on bookings and money), then 2, 3, 4, 6, 7.
Spec 5 is waiting for business approval.

**Why plan this way?** Money and identity are involved. Writing rules down first means no guessing, every rule is
tested, and when someone asks "why does it work like this?", the answer is in the spec.

Each app also has a `CLAUDE.md` (how to work on the code) and a `README.md` (how to run it).

---

## 4. Every feature, explained

### 4.1 Accounts and sign-in (spec 4 R0, R1)

- **Sign up** with any email + a password you choose, **or** "Continue with Google".
- Google sign-up logs you in at once. A Google user has no password until they use "Forgot password?".
- **Log in** with email + password or Google. Admins: password only, never Google.
- **Change password** (need the current one). This logs out every other device.
- **Forgot password:** enter your email → if the account exists, you get a link. The link works **once**, for
  **1 hour**. The page answers the same whether or not the email exists, so nobody can use it to find out who is
  registered. Using the link logs out every device.
- A new tutor gets a "your application is in" email. **No password is ever emailed.**

### 4.2 Profile pictures (spec 4 R1b)

- JPG, PNG or WebP, max 5 MB, resized to 512×512.
- **Required:** a parent needs one before booking or posting a job; a tutor needs one before the NIN step.
- Google sign-up offers the Google photo as the starting picture.
- Admins can remove an inappropriate picture.

### 4.3 Tutor onboarding checklist (spec 4 R2)

A new tutor walks through 5 steps, shown as a checklist on their dashboard:

1. **Profile**: picture + at least one offer
2. **NIN**: identity check
3. **Certificates**: at least one verified by an admin
4. **Quiz**: pass the qualifying exam
5. **Waiting for admin review** → admin approves → "Verified tutor"

Until approved, the tutor is `pending` and **invisible** in tutor search. The admin **cannot** approve unless NIN,
a certificate and the exam are all done (409 error naming what's missing).

### 4.4 NIN verification (spec 4 R3)

**In simple words:** the tutor types their national ID number and takes a selfie. We ask Dojah (an identity
company) "is this a real NIN, is the name exactly the same, and is this the same face?" All three must be yes.

Rules:
- Name must match **exactly** (only capital letters and extra spaces are ignored).
- No admin override. Fail = can't continue.
- On a name mismatch we say "Your name doesn't match your NIN record" but **never show the real name** (so
  nobody can type a stranger's NIN to learn their name).
- After verifying, the tutor's name is **locked** (only an admin can change it).
- One NIN = one TutorLink account.
- **Max 3 attempts per 24 hours** (each check costs money).
- We store only: yes/no, last 4 digits, a keyed hash of the NIN, Dojah's reference, the time.
  **Never** the full NIN, the NIN photo or the selfie.

### 4.5 Certificates (spec 4 R4)

- Upload PDF/JPG/PNG, max 10 MB. Types: WAEC, NECO, NABTEB, NCE, Degree, PGDE, TRCN, Other.
- For WAEC/NECO: exam number, year and **result-checker PIN** (so the admin can check the result on the exam
  body's website). The PIN is **encrypted** in the database and **deleted** after review.
- Admin marks it verified or rejected (with a note). The tutor can re-upload a rejected one.
- Files are private: only the tutor and admins can open them, through short-lived links.

### 4.6 The qualifying exam (spec 4 R5)

**In simple words:** a 20-question test. A robot (Claude AI) writes the questions, a second robot answers them
without seeing the answer key, and we keep only questions where both robots agree.

- 20 questions: 10 general reasoning + 10 from the tutor's own subjects and levels.
- 30 minutes, **timed on the server** (you can't cheat by changing your computer's clock).
- Pass mark: 70% (14/20).
- Correct answers are **never** sent to the browser, not even after submitting (you only see your score), so the
  question bank stays secret.
- Up to 6 attempts, then locked for 24 hours, then 6 more.
- The question bank tops itself up in the background: at least 200 questions per subject+level in use, and 300
  general reasoning.
- Admins can browse the bank and retire bad questions.
- If there aren't enough questions yet: "Your exam is being prepared", and generation starts immediately.

### 4.7 Tutor offers (spec 1 R0)

An **offer** = one or more subjects + one level + weekly time windows + **one price per lesson**.
Example: "Maths & Physics, SS level, Mon/Wed 4–7pm, ₦5,000 per lesson".
A tutor can have many offers and change them anytime. Changes **never** affect existing bookings (they keep a copy).

### 4.8 Bookings (spec 1 R2)

The life of a booking:

```
requested ──(tutor accepts)──▶ accepted (awaiting payment) ──(first period paid)──▶ active ──▶ ended
    │                              │                                                  │
    ├─(tutor declines)─▶ declined   └─(not paid 24h before 1st lesson)─▶ released      ├─▶ paused (next period unpaid)
    └─(72h no answer)──▶ expired                                                      └─ paused 7 days ─▶ ended
                                                                   (parent can also cancel → cancelled)
```

To request a booking, the parent picks: tutor, offer, subjects, weekly slots, start date, billing period
(daily/weekly/monthly), mode (online/offline), and writes the **child's strengths and weaknesses** (10–1,000 chars each).

Rules:
- Slots must fit inside the offer's windows and must not clash with the tutor's other bookings (checked on request **and** on accept).
- Tutor has **72 hours** to answer.
- First period must be paid **24 hours before the first lesson**, or the booking is released.
- Paying a period **creates its lessons, already confirmed**. No extra confirm step.
- Parent cancels with **48+ hours' notice** → those lessons are refunded (via an admin-approved refund request).
- Either side can end a booking.

### 4.9 Paying (spec 1 R3)

**In simple words:** each parent gets their **own bank account number** (from Paystack). When they send money
to it, it shows up as their TutorLink balance. Whenever the balance is enough to pay a period that's due,
we pay it automatically.

- The account number is created the first time one of their bookings is accepted.
- Paystack tells us about the money with a **webhook** (`charge.success`). We check it's really from Paystack,
  process it only once, and double-check with Paystack's API before crediting.
- Every change to the balance is a **ledger entry** (deposit, period payment, refund, withdrawal, withdrawal
  reversal). Balance = sum of entries. Always.
- Next period can be paid once the current one starts; deadline is 24h before its first lesson. Reminders are sent.
  Unpaid → booking paused. Paused 7 days → ended.
- Parents can **withdraw** their balance to a bank account (admin sends it).
- **No cards. Ever.** (A non-goal in the spec.)

### 4.10 Lessons (spec 1 R4, spec 3)

- Tutor must submit a **report** within **24 hours** after the lesson (topic covered + homework).
- **Online lessons:** the report can't be submitted until the **recording** is uploaded.
- No report in 24h → lesson **flagged** to admin, tutor's earning **held**.
- After the report, the parent has **24 hours** to report a problem. No problem → earning becomes **payable**.

### 4.11 Online vs offline (spec 3)

- **Offline (home):** tutor sees the parent's address only after the first period is paid.
- **Online:** tutor sets a meeting link (https only, e.g. Google Meet or Zoom); the parent sees it after payment.
- Online bookings need the parent to tick a **recording consent** ("Lessons will be recorded and kept for
  review"). The time and text are stored.
- Recordings: MP4/WebM/MOV, max 2 GB, uploaded **straight from the browser to the storage bucket** (never through
  our server). Viewing links expire after 15 minutes. Deleted **90 days** after the lesson (kept longer if a
  problem is open).

### 4.12 Problems and refunds (spec 1 R5)

- Parent reports: tutor absent, late/left early, agreement broken, or other (with a description).
- While open, the tutor's earning is **on hold**.
- Admin decides: **Refund** (P goes back to parent's balance, tutor earns nothing), **Reschedule** (new time), or
  **Reject** (lesson stands, earning payable).
- Refunds give back **P, not P + parent fee**.

### 4.13 Tutor payouts (spec 1 R6)

- Tutor adds bank details. Paystack checks the account name matches the tutor's name (admin can override with a note).
- Admin payouts page: payable earnings per tutor, due **48 hours after the last lesson of the billing period**; overdue ones highlighted.
- Admin either **Sends via Paystack** (transfer; result comes by webhook) or **Marks as paid** (paid outside, with a note).
- An earning is paid **at most once**. A failed transfer makes it payable again.

### 4.14 Job posts (spec 2)

**In simple words:** instead of searching, a parent writes "I need a Maths tutor, Tuesdays, ₦4,000 per lesson",
and tutors apply.

- Statuses: `pending → open → ongoing → completed`, or `rejected` (admin) or `closed` (parent).
- **Every job is checked by an admin** before tutors see it.
- Only **approved** tutors can browse and apply (once per job, optional note ≤1,000 chars, no clashes allowed).
- Tutors see: P, their own fee and earning, the parent's **first name + photo**, area, child's strengths/weaknesses.
  **Never** the parent's surname, address, phone, email, fee or total.
- Parent picks an applicant → a booking is created straight in "accepted (awaiting payment)". Job → `ongoing`.
  Other applicants are told. If unpaid/released → job goes back to `open`. Booking ends → job `completed`.

### 4.15 Reviews

One review per parent per tutor, rating 1–5. Shown on the tutor's profile.

### 4.16 Notifications (spec 1 R7)

Every important event creates an **in-app notification** (the bell icon) and an **email** (via Resend). Emails
are sent only **after** the database transaction succeeds (so we never email about something that got rolled back).

### 4.17 Feedback and the help assistant (spec 6)

- Parents and tutors send feedback (problem, suggestion, praise, question), 10–2,000 chars, max **10 per hour**.
- Admins see **Waiting** and **Answered** tabs and reply once. The user gets the reply in-app and by email.
- **Help chat:** Claude answers "how does TutorLink work?" questions from a fixed product description. It **can't
  see** the user's account or money and never states fee percentages. "Send to the TutorLink team" turns the chat
  into feedback. Max 30 questions per hour.

### 4.18 Subjects and legal pages (spec 7)

- Subjects live in the database (Nigerian curriculum or International). Admins add/remove/restore them. Removed
  subjects stay on existing offers. Offers and jobs only accept offered subjects (422 otherwise).
- Privacy notice, terms and disclaimer are edited by admins in **plain text** (`## ` heading, `- ` bullet,
  `**bold**`). **No HTML**, so no one can inject scripts. Every version is kept.
- A document still containing "[… to be filled in]" shows a **draft banner**. (You must fill these before launch!)

---

## 5. The money maths

| Symbol | Meaning | Who sees it |
|---|---|---|
| **P** | Agreed price per lesson | Everyone |
| **S%** | Parent fee (default 10%) | Admin only |
| **T%** | Tutor fee (default 8%) | Tutor + admin |

- Parent pays per lesson: **P × (1 + S%)**
- Tutor earns per lesson: **P × (1 − T%)**
- TutorLink keeps: the difference.

**Example:** P = ₦5,000, S = 10%, T = 8% → parent pays **₦5,500**, tutor gets **₦4,600**, TutorLink keeps **₦900**.

- Admin can change S and T (0–50%). New rates only apply to bookings accepted **after** the change; an accepted
  booking **freezes** its rates.
- **Who sees what is enforced by the API**, not only hidden in the UI (see 9.3).
- Money is stored as `NUMERIC` and handled as Python `Decimal`, never float. Converted to kobo (×100, integer)
  only when talking to Paystack.

---

## 6. The big picture: how the pieces talk

```
        ┌───────────────────────────┐            ┌─────────────────────────────┐
Browser │  Frontend (Next.js)       │  HTTPS     │  Backend API (FastAPI)       │
───────▶│  tutorlink.ng  (Vercel)   │──────────▶ │  api.tutorlink.ng (Render)   │
        │  pages, forms, UI         │  JSON +    │  rules, money, security      │
        └───────────────────────────┘  cookie    │  + background job loop       │
                 │                               └──────┬───────────────────────┘
                 │ direct upload/download                │
                 │ (short-lived signed URLs)             │ SQL
                 ▼                                       ▼
        ┌─────────────────────┐               ┌──────────────────────┐
        │ Cloudflare R2 bucket│               │ PostgreSQL 16         │
        │ photos, certificates│               │ (Render)              │
        │ lesson recordings   │               └──────────────────────┘
        └─────────────────────┘
                                   Backend also calls:
                                   Paystack (accounts, transfers) ◀── webhooks
                                   Resend (emails) · Dojah (NIN) · Google (sign-in) · Anthropic Claude (exam, help)
```

**In simple words:** the frontend is the shop window, the backend is the shop's brain and safe, the database is
the notebook where everything is written, and the bucket is the storage room for files.

---

## 7. Folder structure

```
tutorlink/
├── README.md                 project overview + ERD (database diagram)
├── note.md                   this file
├── specs/                    the 7 feature specs (the "recipes")
├── tutorlink.code-workspace  VS Code workspace
├── backend/                  FastAPI API
│   ├── Dockerfile            how to build the production container
│   ├── docker-compose.yml    LOCAL ONLY: app + Postgres + Adminer
│   ├── pyproject.toml, uv.lock   Python dependencies (locked versions)
│   ├── .env.example          every setting, with explanations
│   ├── alembic.ini, alembic/versions/0001…0023   database migrations
│   ├── app/
│   │   ├── main.py           creates the app: CORS, security headers, request IDs, scheduler
│   │   ├── api.py            plugs every router in under /v1, plus /health
│   │   ├── jobs.py           background jobs
│   │   ├── core/             shared tools: config, security, deps (auth), clock, storage,
│   │   │                     paystack, dojah, google, claude
│   │   ├── db/               database engine, session, base helpers, model registry
│   │   ├── domains/          one folder per business area (see 9.1)
│   │   └── scripts/create_admin.py
│   └── tests/                416 tests
└── frontend/                 Next.js app
    ├── app/                  pages (routes)
    ├── components/           reusable UI pieces
    ├── hooks/                useAuth, useSubjects, useToast
    ├── lib/                  ALL API calls + helpers
    ├── types/index.ts        every API type
    ├── middleware.ts         route protection by role
    ├── next.config.mjs       security headers (CSP etc.)
    ├── public/               images
    └── tailwind.config.ts, components.json (shadcn), tsconfig.json, .eslintrc.json
```

---

## 8. Backend: stack and why

| Thing | What it is (simple) | Why we chose it |
|---|---|---|
| **Python 3.11** | The programming language | Readable, huge ecosystem, great for APIs |
| **FastAPI** | Framework for building the API | Fast, automatic request validation with Pydantic, automatic API docs at `/docs`, dependency injection for auth |
| **uvicorn[standard]** | The web server that runs FastAPI | The standard ASGI server for FastAPI; `[standard]` adds faster parts (uvloop, httptools) |
| **SQLModel** | Lets Python classes be database tables | Same class works as a table *and* a validation model (built on SQLAlchemy + Pydantic), so less duplicate code |
| **PostgreSQL 16** | The database | Reliable transactions (essential for money), `NUMERIC` for exact money, row locks, advisory locks, enums, arrays |
| **psycopg[binary]** | Driver: Python ↔ Postgres | The modern Postgres driver (v3) |
| **Alembic** | Database migrations | Versioned, repeatable schema changes (`0001` … `0023`) |
| **pydantic-settings** | Reads settings from `.env` | Typed settings + validation; the app refuses to start with bad production settings |
| **PyJWT** | Makes and checks login tokens (JWT) | Simple, well-maintained; also verifies Google ID tokens (RS256 with Google's public keys) |
| **passlib[bcrypt]** + **bcrypt==4.0.1** | Password hashing | bcrypt is slow on purpose, so stolen hashes are hard to crack. bcrypt is pinned at 4.0.1 because newer bcrypt versions don't work properly with passlib |
| **cryptography** | Encryption | Fernet (AES + HMAC) encrypts WAEC/NECO checker PINs |
| **httpx** | Makes HTTP calls | Calls Paystack, Dojah and Google; also used by the test client |
| **resend** | Sends emails | Simple email API with good deliverability |
| **boto3** | Talks to S3-compatible storage | Cloudflare R2 and Backblaze B2 speak the S3 language; boto3 makes presigned URLs |
| **pillow** | Image processing | Resizes profile pictures to 512×512 and re-saves them as clean JPEGs |
| **python-multipart** | Reads file uploads/forms | FastAPI needs it for `UploadFile` |
| **email-validator** | Checks email format | Powers Pydantic's `EmailStr` |
| **anthropic** | Claude API client | Writes and checks exam questions; answers the help chat |
| **pytest** (dev) | Test runner | The Python standard |
| **uv** | Installs packages, runs commands | Very fast; `uv.lock` pins every version so builds are repeatable |
| **Docker** | Packages the app into a container | Runs the same on my laptop and on Render |

---

## 9. Backend: how the code is organised

### 9.1 Domains (one folder per business area)

`backend/app/domains/`:

| Domain | Handles |
|---|---|
| `auth` | users, sign-up, login, Google, logout, password change/reset, photos (`photos.py`), rate limits (`limits.py`), admin user actions |
| `tutors` | tutor profile, offers, tutor search, vetting (approve/reject), admin name change |
| `onboarding` | the checklist, NIN verification |
| `certificates` | upload + admin review |
| `exam` | question bank, attempts, scoring, generation |
| `bookings` | requests, accept/decline, cancel/end, schedules, periods, refunds (`schedule.py` does the date maths) |
| `job_posts` | jobs, applications, choosing a tutor, admin review (`sync.py` keeps job status in sync with its booking) |
| `lessons` | lesson lists, reports, recordings, problems, admin resolution |
| `payments` | wallet/balance, account numbers, withdrawals, receipts, bank list |
| `payouts` | tutor earnings, bank account, payouts, receipts |
| `fees` | the S% and T% (single row) |
| `reviews` | ratings |
| `notifications` | in-app list + queued emails |
| `feedback` | feedback, admin replies, help chat |
| `content` | subjects + legal documents |
| `files` | local-file stand-in for the bucket (development only) |
| `webhooks` | Paystack webhooks |

### 9.2 Three layers in every domain

**In simple words:** the waiter, the chef and the pantry.

- `router.py` (**the waiter**): HTTP only. Takes the request, checks who you are (`require_roles`), hands it to
  the service, returns the response model.
- `service.py` (**the chef**): all the business rules and database work. Other domains are reached only through
  their `service`.
- `models.py` (**the pantry**): tables and request/response shapes.

**Why:** rules live in one place, are easy to test without HTTP, and routers stay thin.

### 9.3 Important conventions

- **Who sees what:** a booking or lesson has **three response models**: `…ParentView`, `…TutorView`,
  `…AdminView`. A field a reader must not see **doesn't exist** in their model, so it can't leak, even by mistake.
- **Snapshots:** a booking copies price, subjects and slots when requested and freezes fee rates when accepted.
  Lessons copy their prices when created. Later edits never change the past.
- **Time:** always read through `app.core.clock.now()` so tests can "time travel". Instants stored as UTC;
  lesson dates/times are Nigerian time (WAT, UTC+1).
- **Money:** `Decimal`, rounded with `clock.money`, converted to kobo only at Paystack.
- **Balance:** change it only with `payments.add_entry` inside `lock_parent` (a row lock, `SELECT … FOR UPDATE`),
  so two payments at the same moment can't both spend the same naira.
- **Errors:** plain-English messages the frontend shows as-is. 404 = doesn't exist, 403 = not yours / wrong role,
  409 = wrong state, 422 = bad input, 429 = too many tries.
- **IDs:** `tutor_id` and `parent_id` are always `users.id`.

### 9.4 `main.py` (what happens when the app starts)

1. Logging set up.
2. On startup: starts the background job loop (if `RUN_SCHEDULER=true`).
3. In production: **API docs (`/docs`) are turned off** (no free map for attackers).
4. CORS: only `FRONTEND_URL` may call the API from a browser, with cookies.
5. Security headers on every response.
6. Every request gets an `X-Request-ID` (for tracing in logs).
7. Routes mounted under `/v1`; `/health` for health checks.

### 9.5 `core/config.py` (settings)

Reads `.env`. It **refuses to start** if:
- `SECRET_KEY` is missing, shorter than 32 characters, or the example placeholder;
- in production: the 3 extra keys are missing or equal to `SECRET_KEY`; Paystack is in test mode; Dojah is
  sandbox; Resend, the bucket or `COOKIE_DOMAIN` is missing; URLs aren't `https://`.

**Why:** it's better to fail loudly at deploy time than to quietly lose files or accept fake payments.

---

## 10. Database: every table

34 tables. Grouped:

| Group | Tables |
|---|---|
| Users & auth | `users`, `parent_profiles`, `tutor_profiles`, `password_reset_tokens`, `rate_limit_hits` |
| Tutor offers | `tutor_offers`, `tutor_offer_subjects`, `tutor_offer_windows` |
| Onboarding | `nin_verifications`, `certificates`, `exam_questions`, `exam_attempts`, `exam_attempt_questions` |
| Bookings | `bookings`, `booking_slots`, `booking_periods`, `refunds` |
| Lessons | `lessons`, `lesson_issues` |
| Money (parent) | `virtual_accounts`, `wallet_entries`, `withdrawals` |
| Money (tutor) | `tutor_bank_accounts`, `payouts` |
| Settings | `platform_fees` (one row) |
| Jobs | `job_posts`, `job_slots`, `job_applications` |
| Other | `tutor_reviews`, `notifications`, `feedback`, `subjects`, `legal_documents`, `webhook_events` |

Key rules enforced **by the database itself** (unique constraints):
- One profile / bank account / account number per user.
- One period per booking start date; one lesson per booking start time.
- Each `wallet_entries.reference` is unique → a payment can never be applied twice.
- Each `webhook_events.event_id` is unique → a webhook can never be processed twice.
- `lessons.payout_id`: an earning is paid at most once.
- One review per (tutor, parent).

The full diagram (ERD) is in `README.md`.

**Migrations** (`backend/alembic/versions/`): `0001_auth` → `0023_admin_content`, one per build step. Notable:
`0008` bookings & payments, `0011` job posts, `0012` online lessons, `0013` Google, `0014` NIN, `0015` certificates,
`0016` exam, `0019` drops tutor work emails, `0020` rate limits, `0021` token versions, `0022` feedback,
`0023` subjects + legal pages (seeded).

---

## 11. Every API endpoint

All under `/v1` (e.g. `https://api.tutorlink.ng/v1/auth/login`). Plus `GET /health`.

### Auth (`/auth`)
| Method | Path | What |
|---|---|---|
| POST | `/auth/register` | Sign up with email + password |
| POST | `/auth/login` | Log in (sets cookie) |
| POST | `/auth/google/register` | Sign up with Google |
| POST | `/auth/google/login` | Log in with Google |
| POST | `/auth/logout` | Clear cookie |
| POST | `/auth/forgot-password` | Email a reset link |
| POST | `/auth/reset-password` | Set new password from link |
| GET | `/auth/me` | Who am I |
| PUT | `/auth/me/password` | Change password |
| PUT | `/auth/me/photo` | Upload profile picture |
| DELETE | `/admin/users/{user_id}/photo` | Admin removes a picture |

### Tutors (`/tutors`)
| Method | Path | What |
|---|---|---|
| POST | `/tutors/profile` | Create/update tutor profile |
| GET/POST | `/tutors/profile/offers` | List / add offers |
| PUT/DELETE | `/tutors/profile/offers/{offer_id}` | Edit / remove offer |
| GET | `/tutors` | Search approved tutors (parents/admins only) |
| GET | `/tutors/{tutor_id}` | Tutor public profile |
| PATCH | `/tutors/{tutor_id}/vet` | Admin approves/rejects |
| GET | `/tutors/{tutor_id}/schedule` | Tutor's busy/free weekly times |
| PUT/GET | `/tutors/{tutor_id}/reviews` | Rate / read reviews |
| GET | `/admin/tutors/pending` | Vetting queue |
| PATCH | `/admin/tutors/{tutor_id}/name` | Admin fixes a locked name |

### Onboarding, certificates, exam
| Method | Path | What |
|---|---|---|
| GET | `/onboarding` | Checklist |
| POST | `/onboarding/nin` | NIN + selfie check |
| GET/POST | `/certificates` | List / upload |
| GET | `/admin/certificates` | Review queue |
| PATCH | `/admin/certificates/{id}` | Verify / reject |
| GET | `/exam` | Exam status |
| POST | `/exam/attempts` | Start attempt |
| PUT | `/exam/attempts/{id}/answers` | Save answers |
| POST | `/exam/attempts/{id}/submit` | Submit |
| GET | `/admin/exam/attempts`, `/admin/exam/questions`, `/admin/exam/bank` | Admin views |
| POST | `/admin/exam/questions/{id}/retire` | Retire a question |

### Bookings (`/bookings`)
| Method | Path | What |
|---|---|---|
| POST | `/bookings` | Request booking |
| GET | `/bookings/me` | Parent's bookings |
| GET | `/bookings/tutor/me` | Tutor's bookings |
| GET | `/bookings/{id}` | One booking (shape depends on role) |
| POST | `/bookings/{id}/accept` / `decline` / `cancel` / `end` | Lifecycle actions |
| PUT | `/bookings/{id}/meeting-link` | Tutor sets online link |
| GET | `/admin/bookings` | All bookings |
| GET | `/admin/refunds` | Refund requests |
| POST | `/admin/refunds/{id}/approve` / `reject` | Decide refund |

### Jobs (`/jobs`)
| Method | Path | What |
|---|---|---|
| POST | `/jobs` | Post a job |
| GET | `/jobs` | Tutor browses open jobs |
| GET | `/jobs/me` | Parent's jobs |
| GET | `/jobs/applications/me` | Tutor's applications |
| GET/PUT | `/jobs/{id}` | View / edit |
| POST | `/jobs/{id}/close` / `apply` / `withdraw` | Actions |
| GET | `/jobs/{id}/applications` | Parent sees applicants |
| POST | `/jobs/{id}/applications/{application_id}/choose` | Pick tutor → booking |
| GET | `/admin/jobs` | Review queue |
| PATCH | `/admin/jobs/{id}` | Approve / reject |

### Lessons (`/lessons`)
| Method | Path | What |
|---|---|---|
| GET | `/lessons/me`, `/lessons/tutor/me` | Lesson lists |
| POST | `/lessons/{id}/report` | Tutor report |
| POST | `/lessons/{id}/recording/upload` | Get upload URL |
| POST | `/lessons/{id}/recording/complete` | Confirm upload |
| GET | `/lessons/{id}/recording` | Get 15-min viewing link |
| POST | `/lessons/{id}/problem` | Parent reports problem |
| GET | `/admin/lessons`, `/admin/issues` | Admin views |
| POST | `/admin/lessons/{id}/resolve` | Refund / reschedule / reject |

### Wallet (parent money) and banks
| Method | Path | What |
|---|---|---|
| GET | `/wallet/me` | Balance + entries |
| POST | `/wallet/me/account-number` | Get dedicated account number |
| POST/GET | `/wallet/me/withdrawals` | Request / list withdrawals |
| GET | `/wallet/me/receipts/{entry_id}` | Receipt |
| GET | `/banks` | Nigerian bank list |
| GET | `/admin/withdrawals` | Queue |
| POST | `/admin/withdrawals/{id}/send` / `mark-paid` / `reject` | Handle |

### Earnings (tutor money)
| Method | Path | What |
|---|---|---|
| GET | `/earnings/me` | Earnings |
| GET/PUT | `/earnings/me/bank-account` | Bank details |
| GET | `/earnings/me/payouts` | Payout history |
| GET | `/earnings/payouts/{id}/receipt` | Receipt |
| GET | `/admin/payouts/due`, `/admin/payouts` | Due / history |
| POST | `/admin/payouts` | Pay a tutor |
| POST | `/admin/tutors/{tutor_id}/bank-account/override` | Override name check |

### Everything else
| Method | Path | What |
|---|---|---|
| GET/PUT | `/admin/fees` | Read / change S% and T% |
| GET | `/notifications/me` | Notification list |
| POST | `/notifications/{id}/read`, `/notifications/me/read-all` | Mark read |
| POST | `/feedback`; GET `/feedback/me` | Send / list feedback |
| POST | `/help/chat` | Help assistant |
| GET | `/admin/feedback`; POST `/admin/feedback/{id}/reply` | Admin side |
| GET | `/subjects` | Offered subjects (public) |
| GET | `/legal/{kind}` | privacy / terms / disclaimer (public) |
| GET/POST/PATCH | `/admin/subjects`, `/admin/subjects/{id}` | Manage subjects |
| GET/POST | `/admin/legal/{kind}` | Versions / publish |
| GET/PUT | `/files/{key}` | Local file stand-in (dev only, 404 when a bucket is configured) |
| POST | `/webhooks/payment` | Paystack webhook |
| GET | `/health` | `{"status":"ok","db":"connected"}` or 503 |

In development, open `http://localhost:8000/docs` to try every endpoint.

---

## 12. Background jobs

**In simple words:** a little robot inside the backend wakes up **every 60 seconds** and asks "has any deadline
passed?" Then it does the chores.

`backend/app/jobs.py` → `run_all` does, in order:

1. Expire booking requests not answered in 72h
2. Release/pause bookings that missed payment deadlines
3. Create next billing periods
4. Pay due periods from balances
5. Send payment reminders
6. Flag lessons with no report after 24h
7. Make earnings payable 24h after a report with no problem
8. End finished bookings
9. Delete recordings older than 90 days
10. Close timed-out exam attempts
11. Delete old rate-limit records
12. (+ top up the exam question bank, in the background)

**Important design choices:**
- **Catch-up and idempotent:** each job asks "what *should* be true now?" and fixes it. Running twice changes
  nothing; if the server was down for an hour, the next run catches up.
- **Postgres advisory lock:** only one process runs the jobs at a time, even with several servers.
- Runs **inside the API process** (a thread), so no extra worker service to pay for. Trade-off: the server must be
  always-on (no "sleeping" free plans).
- Manual run: `uv run python -m app.jobs`.

---

## 13. Outside services we use

| Service | Used for | Code (only place it's called) |
|---|---|---|
| **Paystack** | Dedicated account numbers, verifying deposits, bank list, account-name lookup, transfers to tutors/parents, webhooks | `core/paystack.py`, `domains/webhooks` |
| **Resend** | Emails | `domains/notifications` |
| **Dojah** | NIN + selfie verification | `core/dojah.py` |
| **Google** | "Continue with Google" | `core/google.py` (backend), `lib/google.ts` + `GoogleButton.tsx` (frontend) |
| **Anthropic Claude** | Exam questions + checking them; help chat | `core/claude.py` |
| **Cloudflare R2** (or Backblaze B2) | Photos, certificates, recordings | `core/storage.py` |

**Why one file per service?** One place to change, one place to fake in tests, one place to audit.
Without keys in development: emails are logged instead of sent, files go to a local folder, Claude features say
they're off.

---

## 14. Frontend: stack and why

| Thing | What it is (simple) | Why |
|---|---|---|
| **Next.js 15 (App Router)** | Framework for React websites | File-based routes, server rendering, middleware, image optimisation, and Vercel hosts it with zero setup |
| **React 19** | Builds the UI from components | Industry standard |
| **TypeScript (strict)** | JavaScript with types | Catches mistakes before running; `types/index.ts` mirrors the API |
| **Tailwind CSS 3** | Styling with small class names | Fast to build, consistent spacing/colours, no huge CSS files |
| **tailwindcss-animate** | Animation classes | Used by shadcn dialogs/menus |
| **shadcn/ui** | Copy-in UI components (`components/ui/`) | We own the code (not a black-box library), built on Radix |
| **Radix UI** (`dialog`, `dropdown-menu`, `label`, `select`, `slot`, `tabs`) | Unstyled, accessible building blocks | Keyboard navigation, focus handling and screen readers done right |
| **class-variance-authority**, **clsx**, **tailwind-merge** | Helpers to combine class names | Button variants etc.; `cn()` in `lib/utils.ts` |
| **React Hook Form** + **@hookform/resolvers** + **Zod** | Forms + validation rules | Fast forms; Zod schemas check input before sending |
| **Axios** | Makes API calls | Interceptors (global 401 handling), `withCredentials` for cookies |
| **sonner** | Toast pop-ups | Simple success/error messages |
| **lucide-react** | Icons | Clean, consistent icons |
| **next-themes** | Light/dark mode | Remembers the choice, no flash on load |
| **ESLint** (`eslint-config-next`) | Code checker | Catches bugs and bad patterns |
| **PostCSS** | CSS processing | Required by Tailwind (versions pinned via `overrides` for security fixes) |

**Why a separate frontend and backend (not one Next.js app doing everything)?** The backend holds money and
identity rules; Python has the libraries we need (Paystack, Pillow, Anthropic, crypto), and the API can later
serve a mobile app too.

---

## 15. Frontend: every page (route)

| Route | Who | What |
|---|---|---|
| `/` | Everyone | Home page with hero slideshow |
| `/login`, `/register` | Visitors | Log in / sign up (email or Google), photos beside the form |
| `/forgot-password`, `/reset-password` | Visitors | Password reset |
| `/tutors` | Parents, admins | Search tutors with filters (offers "Post a request" if nothing fits) |
| `/tutors/[id]` | Parents, admins | Tutor profile, offers, reviews, badges, booking form |
| `/privacy`, `/terms`, `/disclaimer` | Everyone | Legal pages (from the API) |
| `/dashboard/parent` | Parent | Overview |
| `/dashboard/parent/bookings` | Parent | Bookings, pay info, cancel/end |
| `/dashboard/parent/lessons` | Parent | Lessons, reports, recordings, report a problem, rate tutor |
| `/dashboard/parent/wallet` | Parent | Balance, account number, entries, withdrawals |
| `/dashboard/parent/jobs`, `/jobs/new`, `/jobs/[id]` | Parent | Job posts, create, see applicants |
| `/dashboard/parent/feedback` | Parent | Feedback |
| `/dashboard/tutor` | Tutor | Onboarding checklist / overview |
| `/dashboard/tutor/profile` | Tutor | Profile, offers, photo, NIN, certificates |
| `/dashboard/tutor/exam` | Tutor | Qualifying exam |
| `/dashboard/tutor/bookings` | Tutor | Requests, accept/decline, meeting links |
| `/dashboard/tutor/lessons` | Tutor | Reports, recording uploads |
| `/dashboard/tutor/earnings` | Tutor | Earnings, bank account, payouts |
| `/dashboard/tutor/jobs`, `/jobs/[id]` | Tutor | Browse and apply to jobs |
| `/dashboard/tutor/feedback` | Tutor | Feedback |
| `/admin/tutors` | Admin | Vetting queue |
| `/admin/certificates` | Admin | Certificate review |
| `/admin/exam` | Admin | Attempts + question bank |
| `/admin/jobs` | Admin | Job review |
| `/admin/problems` | Admin | Lesson problems/flags |
| `/admin/refunds` | Admin | Refund requests |
| `/admin/payouts` | Admin | Pay tutors |
| `/admin/withdrawals` | Admin | Parent withdrawals |
| `/admin/fees` | Admin | S% and T% |
| `/admin/subjects` | Admin | Subject list |
| `/admin/legal` | Admin | Edit legal pages |
| `/admin/feedback` | Admin | Answer feedback |
| `/receipts/wallet/[id]`, `/receipts/payouts/[id]` | Owner | Printable receipts |
| `not-found.tsx`, `error.tsx`, `global-error.tsx` | Everyone | 404 and error pages |

`app/layout.tsx` = the shell around every page (fonts, theme, toasts). `dashboard/parent/layout.tsx`,
`dashboard/tutor/layout.tsx` and `admin/layout.tsx` add the sidebar for each role.

### `middleware.ts` (the doorman)
Runs **before** a page loads:
- Logged-in user opens `/login` or `/register` → sent to their own dashboard.
- `/tutors…` → visitors are sent to sign up as a parent; tutors are sent to their dashboard.
- `/dashboard`, `/admin`, `/receipts` → need the login cookie, and **the right role** for that area.
- It reads the role from the token **only for routing**. The **backend still checks every request**. The doorman
  is for convenience, the backend is the real security.

---

## 16. Frontend: every component, hook and lib file

### `components/`
| Folder | Components |
|---|---|
| `auth/` | `AuthShell` (login/register layout with photos), `GoogleButton` |
| `bookings/` | `BookingCard`, `MeetingLinkEditor` |
| `feedback/` | `FeedbackCard`, `FeedbackPage`, `HelpChat` (the Claude assistant) |
| `home/` | `HeroSlideshow` |
| `jobs/` | `JobForm`, `JobSummary`, `TutorJobActions` |
| `layout/` | `DashboardShell`, `Navbar`, `Sidebar` (the one list of each role's links), `Footer`, `NotificationBell`, `ThemeToggle` |
| `legal/` | `LegalPage`, `LegalText` (renders plain text safely, shows draft banner) |
| `lessons/` | `LessonCard`, `RecordingPlayer` |
| `payments/` | `AccountNumberCard` |
| `receipts/` | `ReceiptShell` |
| `reviews/` | `RateTutorDialog`, `ReviewList`, `StarRating` |
| `shared/` | `Avatar`, `ChangePasswordCard`, `Choice`, `ConfirmDialog`, `NoteDialog`, `EmptyState`, `FormField`, `LoadingSpinner`, `PageHeader`, `PhotoUploader`, `RecordingConsent`, `StatCard`, `StatusBadge` |
| `tutors/` | `AvailabilityView`, `BookingForm`, `CertificatesSection`, `OfferFields`, `OnboardingChecklist`, `SelfieCamera`, `TutorCard`, `TutorFilters`, `VerificationBadges` |
| `ui/` | shadcn: `badge`, `button`, `card`, `dialog`, `dropdown-menu`, `input`, `label`, `select`, `sonner`, `table`, `tabs`, `textarea` |

### `hooks/`
- `useAuth`: current user (`/auth/me`), login (redirects by role), logout.
- `useSubjects`: offered subjects from the API.
- `useToast`: toast helper.

### `lib/` (the only place that talks to the API)
`api.ts` (Axios instance), and one file per area: `auth`, `bookings`, `certificates`, `content`, `exam`,
`feedback`, `google`, `jobs`, `lessons`, `notifications`, `onboarding`, `payouts`, `reviews`, `tutors`, `wallet`.
Helpers: `convert.ts` (money strings → numbers), `format.ts` (₦ formatting, dates, status labels), `utils.ts` (`cn()`).

**Why all API calls in `lib/`?** Pages never touch Axios. If an endpoint changes, you fix one file.

### `lib/api.ts` explained
- `baseURL` = `NEXT_PUBLIC_API_URL`.
- `withCredentials: true` → the browser sends the login cookie.
- Header `X-Requested-With: TutorLink` on every request (CSRF protection, see 17).
- Any 401 (session ended) → logs out and goes to `/login` (except on login pages themselves).
- `errorMessage()` shows the backend's plain-English `detail`.

---

## 17. Security: every protection and why

> **Golden rule:** the frontend is for convenience; **the backend enforces everything.** Anyone can call the API
> directly, so every rule is checked there.

### 17.1 Passwords
| What | Why |
|---|---|
| **bcrypt hashing** | We never store passwords, only a slow one-way hash. A stolen database doesn't reveal them. |
| `password_hash` is in **no** response model | It can never leak through the API. |
| No password is ever emailed | Emails can be read by others. |
| Changing/resetting a password **logs out every device** (`token_version`) | If someone stole your session, they lose it. |

### 17.2 Login tokens (JWT) and sessions
| What | Why |
|---|---|
| JWT signed with `SECRET_KEY` (HS256), containing user id, role, version, expiry | The server can trust it without a database lookup for the signature; tampering breaks the signature. |
| Tokens last 24h; **admin tokens 4h** | Admin powers (approve tutors, send money) are dangerous, so shorter exposure. |
| Each request re-checks the user exists, is active, and `token_version` matches | Lets us revoke tokens (JWTs can't normally be revoked). |
| **httpOnly cookie** (`tutorlink_token`) | JavaScript can't read it, so even an injected script (XSS) can't steal it. Never in localStorage. |
| Cookie `Secure` (HTTPS only) in production, `SameSite=Lax` | Not sent over plain HTTP; not sent on most cross-site requests. |
| `COOKIE_DOMAIN` = shared parent domain | Lets `tutorlink.ng`'s middleware see the cookie set by `api.tutorlink.ng`. |

### 17.3 CSRF (Cross-Site Request Forgery)
**In simple words:** a bad website could try to make *your* browser send "pay money" to TutorLink while you're
logged in. We stop it.

**How:** every cookie-authenticated POST/PUT/PATCH/DELETE must carry the header `X-Requested-With: TutorLink`.
Browsers only let another website send custom headers after a **CORS** check, and CORS allows **only**
`FRONTEND_URL`. So evil sites can't send it → 403.

### 17.4 CORS
Only `FRONTEND_URL` may call the API from a browser with credentials.

### 17.5 Authorisation (who can do what)
- `require_roles([...])` on every protected route → 403 for the wrong role.
- Services check **ownership** ("is this your booking?") → 403 otherwise.
- **Per-role response models** hide fees/earnings/bank numbers (spec 1 R1), tested.
- Tutor bank number: only admins see it in full; tutors see last 4 digits.
- Tutors can't browse tutors; visitors can't see tutors at all.
- Parent's private details (surname, address, phone, email) are never shown to tutors on jobs; address only after payment.

### 17.6 Rate limiting (stops guessing and spam)
Stored in Postgres (`rate_limit_hits`):

| Rule | Limit |
|---|---|
| Failed logins per email | 10 / 15 min |
| Logins per IP | 20 / 15 min |
| Google sign-ins per IP | 20 / 15 min |
| Sign-ups per IP | 10 / hour |
| Reset emails per email | 3 / hour |
| Reset emails per IP | 10 / hour |
| Reset link uses per IP | 10 / 15 min |
| Feedback per user | 10 / hour |
| Help chat per user | 30 / hour |
| NIN checks per tutor | 3 / 24h (costs money) |
| Exam attempts | 6, then 24h lock |

`TRUST_PROXY_HEADERS=true` behind Render/Cloudflare so we count the **real** visitor IP, not the proxy's.

### 17.7 Password reset
- Random token (`secrets.token_urlsafe`), only its **SHA-256 hash** stored (a database leak doesn't give working links).
- One use, 1 hour.
- Same answer for known/unknown emails (no "account enumeration").

### 17.8 Google sign-in
Verifies the ID token's **signature** (Google's public keys), **audience** (our Client ID), **issuer**, **expiry**, and
`email_verified`. Forged/expired/wrong-audience tokens → 401. Admins can't use Google.

### 17.9 Payments and webhooks (the most important)
| What | Why |
|---|---|
| Webhook signature: **HMAC-SHA512** of the raw body with our secret, compared in constant time | Proves it came from Paystack; constant-time stops timing attacks. |
| Rejected if the secret is empty/placeholder | Otherwise anyone could sign a fake "payment succeeded". |
| `webhook_events` unique `event_id`, inserted in the **same transaction** as the money movement | A webhook delivered twice is applied once. |
| Deposits **re-verified** with Paystack's API before crediting | Even a valid-looking event is double-checked. |
| Unique `wallet_entries.reference` | The same money can't be added twice. |
| `lock_parent` row lock | Two simultaneous actions can't double-spend a balance. |
| `lessons.payout_id` + failed transfer → payable again | Tutor paid at most once, never lost. |
| Money as `Decimal`/`NUMERIC` | Floats make rounding errors (0.1 + 0.2 ≠ 0.3). |
| **No card payments** | No card data, no PCI compliance burden. |

### 17.10 Sensitive data (NIN, PINs)
| What | Why |
|---|---|
| Full NIN, NIN photo, selfie **never stored** | Can't leak what you don't have (data minimisation, Nigeria Data Protection Act). |
| NIN stored as a **keyed hash** (HMAC with `NIN_HASH_KEY`) | Only 10¹¹ NINs exist: a plain hash could be brute-forced; a keyed one can't without the key. Still lets us enforce "one NIN, one account". |
| Name mismatch doesn't reveal the real name | Can't use TutorLink to look up strangers. |
| WAEC/NECO PIN **encrypted** (Fernet, `FIELD_ENCRYPTION_KEY`), deleted after review | Kept only as long as needed. |
| **Separate keys per job** (`SECRET_KEY`, `FILE_SIGNING_KEY`, `FIELD_ENCRYPTION_KEY`, `NIN_HASH_KEY`) | Leaking one doesn't give away the others. Production refuses to start if they're missing or equal. |

### 17.11 Files
| What | Why |
|---|---|
| Private bucket; access only through **short-lived signed URLs** (15 min for recordings/certificates, 6h for photos) | A copied link stops working soon. |
| Uploads go **directly to the bucket** via presigned URL, with type and size fixed in the signature | Our server never handles 2 GB videos; can't upload a different type/size. |
| Re-checked from the stored object before the report is accepted | Don't trust the browser. |
| Certificates checked by **magic bytes** (`%PDF-`, JPEG/PNG headers), not just the file name | A renamed `.exe` isn't accepted. |
| Photos re-encoded by Pillow into a fresh JPEG, EXIF orientation applied | Strips hidden content/metadata (e.g. GPS location) and malformed files. |
| Size limits read with a cap (`MAX_BYTES + 1`) | A huge upload can't exhaust memory. |

### 17.12 Browser security headers
Frontend (`next.config.mjs`):
- **Content-Security-Policy**: scripts only from our site and Google; nobody may frame us; no plugins. (`unsafe-inline` is needed by Next.js.)
- **X-Frame-Options: DENY**: stops clickjacking.
- **X-Content-Type-Options: nosniff**: no content-type guessing.
- **Referrer-Policy**: don't leak full URLs to other sites.
- **Permissions-Policy**: camera only for us (the NIN selfie); no mic, location or payment APIs.
- **Strict-Transport-Security** (production): browsers always use HTTPS.
- `poweredByHeader: false`: don't advertise "Next.js".

Backend (`main.py`): `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
`CSP: default-src 'none'` (it's JSON, it should run nothing), HSTS on HTTPS.

### 17.13 XSS (injected scripts)
- React escapes text by default; we **never** use `dangerouslySetInnerHTML`.
- Legal pages are plain text rendered as React text, never HTML.
- Token in an httpOnly cookie (an XSS can't steal it).

### 17.14 AI safety (prompt injection)
- Subjects in exam prompts come **only** from the admin-kept list, and are fenced off as data.
- Help chat has no access to accounts or money, so it can't leak them.
- A second independent Claude call verifies each exam question; mismatches are discarded.
- Correct answers never reach the browser.

### 17.15 Infrastructure
- Production disables `/docs`, `/redoc` and `/openapi.json`.
- Docker container runs as a **non-root user**; uv version pinned; dependencies locked (`uv.lock`, `package-lock.json`).
- Local Docker ports bound to `127.0.0.1` only.
- `.env` and `.env.local` are git-ignored; `.env.example` has placeholders the app **refuses** to use.
- Config fails fast in production if anything critical is missing or still in test mode.
- `X-Request-ID` on every response for tracing.

---

## 18. Testing

- **416 backend tests**, all passing (`uv run pytest`, ~13 minutes).
- Run against a **real PostgreSQL** (`tutorlink_test` database), not a fake: constraints, locks and enums are
  tested for real. Every migration is run down and back up first.
- Tables truncated before each test (clean slate).
- **Fakes** for outside services: `FakePaystack`, `FakeDojah`, `FakeClaude`, a fake Google key, an `outbox` for emails.
- **`FakeClock`**: `clock.travel(hours=72)` + `run_jobs` tests time rules (expiry, deadlines) instantly.
- **Helpers** build starting states: `approved_tutor`, `accepted_booking`, `paid_booking`, `completed_lesson`, `deposit`…
- Each spec's acceptance criteria → tests (e.g. "a forged webhook doesn't credit", "a parent response has no tutor-fee fields").
- Frontend: `npm run build` = type-check + lint + production build (passing). No automated UI tests yet.

---

## 19. Running it on your computer

```bash
# Backend
cd backend
cp .env.example .env              # set SECRET_KEY and POSTGRES_PASSWORD
docker compose up -d --build      # API (8000) + Postgres (5435) + Adminer (8080)
docker compose exec app uv run alembic upgrade head
docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng

# Frontend
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev                       # http://localhost:3000
```

Tests: `cd backend && uv run pytest` (needs the db container) · `cd frontend && npm run build`
(don't build while `npm run dev` is running: it overwrites `.next`).

---

## 20. Deployment (Vercel + Render)

### Stage 1: the free test site (what we deployed first)

```
https://<site>.vercel.app      → Vercel Hobby (frontend). Forwards /api/v1/* to Render.
https://<api>.onrender.com     → Render Free web service (backend, Docker, Frankfurt)
Neon Postgres (free)           → database, created from Vercel's Storage tab (Frankfurt)
Backblaze B2 (free 10 GB)      → files (private bucket + CORS rule for the site)
```

**Why it looks like this:**
- **No domain yet.** Browsers treat `*.vercel.app` and `*.onrender.com` as separate sites, so a cookie set by the API
  couldn't be read by the site. Fix (PR #5): the site **forwards** `/api/v1/*` to Render (`API_PROXY_TARGET` in
  `next.config.mjs`), so the browser only talks to the site and the login cookie belongs to it. `COOKIE_DOMAIN` is
  then left empty. Every API answer is `Cache-Control: no-store` so Vercel never stores one user's data.
- **No card.** Cloudflare R2 and paid Render plans need a payment method, so: Backblaze B2 (S3-compatible, the
  code already supports it), Neon free Postgres, Render Free.
- **`APP_ENV=staging`**: production mode refuses test Paystack keys and the Dojah sandbox, which is all we have
  until the live approvals arrive.
- **Render Free sleeps** after ~15 min without visitors, which pauses the background jobs. A free uptime monitor
  opens `/health` every 10 minutes to keep it awake. `SCHEDULER_INTERVAL_SECONDS=600` (spec: at least every 15 min)
  keeps the database inside Neon's free compute hours.
- **No pre-deploy command or shell on Render Free**: the Docker Command runs `alembic upgrade head` before starting
  uvicorn, and the first admin is created from my own computer against the Neon database.
- **Email**: without a domain, Resend sends only from `onboarding@resend.dev` and only to my own address.

**Settings:**
- Render: `APP_ENV=staging`, `PORT=8000`, 4 random keys (`SECRET_KEY`, `FILE_SIGNING_KEY`, `FIELD_ENCRYPTION_KEY`,
  `NIN_HASH_KEY`), `DATABASE_URL` (Neon **unpooled**, `postgresql+psycopg://…?sslmode=require`), `BASE_URL`,
  `FRONTEND_URL`, `TRUST_PROXY_HEADERS=true`, `SCHEDULER_INTERVAL_SECONDS=600`, Paystack test keys +
  `PAYSTACK_DVA_BANK=test-bank`, Resend, Google, Anthropic, Dojah sandbox, `STORAGE_*` (B2).
- Vercel: root `frontend`, `NEXT_PUBLIC_API_URL=/api/v1`, `API_PROXY_TARGET=https://<api>.onrender.com`,
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.
- Neon: use the **unpooled** connection; the pooled one (PgBouncer) breaks the scheduler's advisory lock.
- Paystack test webhook: `https://<api>.onrender.com/v1/webhooks/payment`.
- Google: add the Vercel address to "Authorized JavaScript origins".

### Stage 2: real launch (needs a payment method, e.g. a virtual dollar card)
- Buy a domain: site on `tutorlink.ng`, API on `api.tutorlink.ng`, `COOKIE_DOMAIN=tutorlink.ng` (or keep forwarding).
- Vercel Pro (Hobby is non-commercial), an always-on Render plan.
- `APP_ENV=production` with live Paystack (`sk_live_…`, a live `PAYSTACK_DVA_BANK`), live Dojah, Resend with a
  verified domain, `https://` URLs. The app refuses to start until all are set.
- Fill in the 9 "[… to be filled in]" gaps in the legal pages at `/admin/legal`.

---

## 21. Glossary

| Word | Meaning |
|---|---|
| **API** | The backend's set of URLs the frontend calls to get/change data |
| **Endpoint** | One API URL + method, e.g. `POST /v1/bookings` |
| **JWT** | A signed token that says "this is user X with role Y until time Z" |
| **httpOnly cookie** | A cookie JavaScript can't read |
| **CORS** | Browser rule: which websites may call our API |
| **CSRF** | A trick where another site makes your browser act for you |
| **XSS** | Injecting a script into a page |
| **Webhook** | Paystack calling *us* to say "something happened" |
| **Idempotent** | Doing it twice has the same effect as once |
| **HMAC** | A signature made with a secret key, proves who sent something |
| **Hash** | One-way scramble; can't be reversed |
| **Encryption** | Two-way scramble; can be reversed with the key |
| **Migration** | A versioned change to the database structure |
| **Presigned URL** | A temporary link that allows one upload/download without a password |
| **DVA** | Dedicated Virtual Account: the parent's own account number |
| **Ledger** | A list of money entries; the balance is their sum |
| **Advisory lock** | A Postgres "only one at a time" flag |
| **Row lock** (`FOR UPDATE`) | Lock one database row until the transaction ends |
| **CSP** | A header telling the browser which scripts/images may load |
| **HSTS** | A header telling the browser "always use HTTPS" |
| **WAT** | West Africa Time (UTC+1), Nigeria's time zone |
| **Kobo** | 1/100 of a naira; Paystack uses kobo integers |
| **P, S%, T%** | Price per lesson, parent fee, tutor fee |
| **Spec** | Written requirements for a feature |

---

## 22. Questions a senior engineer will ask (with answers)

### Architecture

**Q1. Why a separate FastAPI backend instead of doing everything in Next.js?**
The backend holds money, identity and time-based rules. Python has mature libraries for what we need (Pillow,
cryptography, boto3, Anthropic, Paystack over httpx), FastAPI gives typed validation and auto-docs, and a separate
API can serve a future mobile app. The frontend stays a thin UI.

**Q2. Why a modular monolith, not microservices?**
One small team, one database, strong transactions across domains (a payment touches bookings, wallet and lessons
atomically). Microservices would add network calls, distributed transactions and ops cost for no benefit at this
scale. The domain folders give clean boundaries, so we could split later if needed.

**Q3. How is the backend code structured?**
Domain folders, each with router (HTTP), service (rules + DB), models (tables + schemas). Domains talk only through
each other's `service` modules. Routers are thin; services are testable.

**Q4. Why SQLModel over plain SQLAlchemy or Django ORM?**
One class serves as both a table and a Pydantic model, which fits FastAPI. It's SQLAlchemy underneath, so we can
drop to SQLAlchemy for locks, upserts (`pg_insert`) and complex queries.

**Q5. Why PostgreSQL?**
ACID transactions for money, `NUMERIC` for exact amounts, row locks (`FOR UPDATE`), advisory locks for the
scheduler, unique constraints for idempotency, enums and arrays.

### Money and correctness

**Q6. How do you make sure a payment is never credited twice?**
Three layers: (1) the webhook's event id is inserted into `webhook_events` (unique) in the **same transaction** as
the credit, so a retry hits the unique constraint and changes nothing; (2) every wallet entry has a unique
`reference`; (3) we re-verify the transaction with Paystack's API before crediting.

**Q7. What if a parent's balance is changed by two things at once?**
Every balance change goes through `payments.add_entry` inside `lock_parent`, which takes a row lock
(`SELECT … FOR UPDATE`) on the parent's user row. The second transaction waits, then sees the updated balance.

**Q8. Why store the balance as a ledger instead of a number column?**
Auditability: every naira has a reason and a reference. The balance is the sum of entries, so it can't drift, and
we can always explain it. Tests assert balance = sum of entries after every operation.

**Q9. Why Decimal and not float?**
Floats can't represent 0.1 exactly; rounding errors in money are unacceptable. `Decimal` in Python, `NUMERIC` in
Postgres, kobo integers only at the Paystack boundary.

**Q10. How do you make sure the parent never sees the tutor's fee, and vice versa?**
It's enforced in the API, not the UI: each reader gets a different response model (`ParentView`, `TutorView`,
`AdminView`). A field they mustn't see doesn't exist in their model. Tests check parent-facing responses contain no
tutor fee/earning fields and tutor-facing responses contain no parent fee/total.

**Q11. What happens if the admin changes the fees while bookings are active?**
Nothing changes for them. Fee rates are **frozen on the booking at accept time**, and each lesson copies its
amounts when created. Only bookings accepted later use the new rates.

**Q12. How can a tutor never be paid twice?**
Each lesson has a `payout_id`; once set, the earning isn't payable. A `transfer.failed` webhook clears it, making
it payable again, so the tutor is never lost either.

**Q13. Why no card payments?**
Business decision (spec 1 non-goal): bank transfer is common in Nigeria, cheaper, and we avoid handling card data
(PCI compliance).

### Background jobs

**Q14. How do the time-based rules work (expiry, deadlines)?**
A thread in the API process runs `jobs.run_all` every 60 seconds. Each job is an **idempotent catch-up pass**:
"given the time now, what should be true?" So downtime is harmless; the next run catches up.

**Q15. What if you run two backend instances? Won't jobs run twice?**
No. `run_once` takes a Postgres **advisory lock** (`pg_try_advisory_lock`); a second instance skips that round.

**Q16. Why not Celery/Redis?**
Extra infrastructure to run and pay for. Our jobs are periodic DB sweeps, not a high-volume queue. The advisory
lock gives us safety across instances. If volume grows, moving `run_once` to a separate worker or cron is a small change.

**Q17. How do you test time-based rules?**
All code reads time from `clock.now()`. Tests use a `FakeClock`: `clock.travel(hours=73)`, then run the jobs,
then assert (e.g. the request expired).

### Auth and security

**Q18. Why JWT in an httpOnly cookie instead of localStorage?**
localStorage is readable by any script, so one XSS bug would leak every token. An httpOnly cookie can't be read
by JavaScript.

**Q19. But cookies are vulnerable to CSRF. How do you handle it?**
`SameSite=Lax`, plus every state-changing cookie request must carry `X-Requested-With: TutorLink`. Browsers only
allow cross-site custom headers after a CORS preflight, and CORS allows only our frontend, so a malicious site can't
send it.

**Q20. JWTs can't be revoked. How do you log someone out everywhere?**
Each token contains the user's `token_version`. On password change/reset we increment it; every request compares
the token's version with the database, so old tokens fail immediately.

**Q21. The Next.js middleware reads the JWT without verifying the signature. Isn't that insecure?**
It's only for **routing** (which dashboard to show). It grants no data. Every API call is verified by the backend.
A forged token would show an empty page whose API calls all fail with 401.

**Q22. How do you stop brute-force login attempts?**
Rate limits per email and per IP, stored in Postgres (`rate_limit_hits`), with a separate set for sign-ups, resets,
Google, feedback and help. Behind a proxy we trust `X-Forwarded-For` (only then) to get the real IP.

**Q23. Why store rate limits in Postgres and not Redis?**
We don't run Redis; the volume is small (auth events), and Postgres keeps it consistent across instances. The job
loop deletes old rows.

**Q24. How do you verify Google sign-in?**
The browser gets an ID token from Google; the backend verifies it with Google's public keys (cached JWKS): RS256
signature, audience = our Client ID, issuer = Google, expiry, and `email_verified`.

**Q25. How is the password reset secure?**
Random 32-byte token; only its SHA-256 is stored; one use; 1 hour; rate limited; same response for unknown emails;
using it bumps `token_version` (logs out everywhere).

**Q26. How do you protect the NIN?**
We never store the full NIN, the NIN photo or the selfie. We keep the last 4 digits and an **HMAC keyed hash** so
one NIN can verify only one account. A plain SHA-256 would be brute-forceable (only 10¹¹ possibilities); the key
prevents that.

**Q27. Why separate keys (`SECRET_KEY`, `FILE_SIGNING_KEY`, `FIELD_ENCRYPTION_KEY`, `NIN_HASH_KEY`)?**
Blast radius: a leak of one doesn't compromise the others. Production refuses to start if they're missing or reused.

**Q28. How are file uploads secured?**
Private bucket, presigned URLs that expire (15 min), with content type and size baked into the signature; the stored
object is re-checked before use; certificates are checked by magic bytes; photos are re-encoded by Pillow. Large
files never pass through our API server.

**Q29. Why does the CSP allow `'unsafe-inline'` scripts?**
Next.js injects inline scripts for hydration. The stronger alternative is per-request nonces, which makes every page
dynamic. We accept this trade-off; other layers (React escaping, no `dangerouslySetInnerHTML`, httpOnly cookie)
reduce XSS risk. It's a candidate for hardening later.

**Q30. How do you defend the AI features against prompt injection?**
Nothing a user types reaches the exam prompt: subjects come from the admin-kept list and are fenced as data. The
help assistant has no tools and no access to user data, so even a successful injection can't leak anything. Exam
questions are verified by an independent second call.

**Q31. Why are API docs disabled in production?**
`/docs` gives an attacker a map of every endpoint. Developers use it locally.

### Data and migrations

**Q32. How do you change the database safely?**
Alembic migrations, one per build step, run on deploy (`alembic upgrade head` as Render's pre-deploy command). Tests
run every migration down and up to prove they're reversible.

**Q33. What's a "snapshot" and why?**
A booking copies price, subjects and slots at request time and freezes fees at accept. Lessons copy amounts at
creation. This protects existing agreements from later edits: what the parent agreed to is what they pay.

**Q34. How long do you keep recordings, and why?**
90 days (longer if a problem is open). That's long enough for disputes and limits storage cost and privacy exposure.

### Testing and quality

**Q35. How did you test this?**
416 pytest tests against a real Postgres, with fakes for Paystack, Dojah, Claude, Google and email, and a fake
clock for time. Each spec's acceptance criteria are tests. The frontend is type-checked, linted and built.

**Q36. Why a real database in tests instead of SQLite or mocks?**
We depend on Postgres features (`FOR UPDATE`, advisory locks, enums, `NUMERIC`, unique-constraint behaviour).
Mocks would pass while production broke.

**Q37. What's missing in testing?**
No frontend unit/E2E tests (e.g. Playwright) and no CI pipeline yet. Those are next on the list (see section 23).

### Scale and operations

**Q38. What breaks first under load?**
Probably the single API instance and DB connections. We can add instances (the scheduler is safe thanks to the
advisory lock), add a connection pooler, add indexes from slow-query logs, and move jobs to a worker.

**Q39. How do you debug a production problem?**
Every response has an `X-Request-ID`; logs go to stdout (Render collects them); `/health` checks the database. An
error tracker (e.g. Sentry) is a planned addition.

**Q40. Why Vercel + Render?**
Vercel is the native home of Next.js (zero config, CDN, HTTPS). Render runs our Dockerfile as a long-running
service (needed for the in-process scheduler and webhooks). Both deploy from Git. The test site uses free plans
(Render Free kept awake by an uptime monitor, Neon Postgres, Backblaze B2); launch moves to paid, always-on plans.

**Q41. How does login work when the site and the API are on different hosts?**
Either they share a parent domain (`tutorlink.ng` + `api.tutorlink.ng` with `COOKIE_DOMAIN=tutorlink.ng`), or, as on
the free test site, the site forwards `/api/v1` to the API, so the browser only ever talks to the site and the cookie
is the site's own. `*.vercel.app` and `*.onrender.com` can never share cookies (they're on the Public Suffix List).
The API sends `Cache-Control: no-store` so the forwarding layer never caches a user's answer.

**Q42. How do you handle secrets?**
In the hosting platforms' environment settings, never in Git (`.env` is ignored). `.env.example` has placeholders
that the app detects and refuses.

### Product and process

**Q43. Why write specs first?**
Money and identity rules must be exact. Specs with requirement IDs make rules traceable from spec → code → test,
and acceptance criteria become the tests.

**Q44. Why must tutors pass NIN, certificates AND an exam?**
Trust is the product. Parents let strangers into their homes; the triple check (identity, qualifications, ability)
is the main selling point.

**Q45. Why do tutors report every lesson, with recordings online?**
Parents pay first, so they need proof lessons happened. The 24h problem window and held earnings protect parents;
prepayment protects tutors.

**Q46. What would you do differently / next?**
See section 23: CI, frontend tests, error tracking, CSP nonces, a separate worker, spec 5 (international).

**Q47. Did you use AI to build this? (Be honest.)**
If asked, say how you worked: you wrote and approved the specs, used an AI coding assistant to implement them, and
reviewed and tested the result. Then show you understand the code by explaining any part of it. This document is
here to help with that.

---

## 23. Honest limits and what I'd improve next

| Area | Today | Next step |
|---|---|---|
| CI | None; tests run by hand | GitHub Actions: pytest + `npm run build` on every PR |
| Frontend tests | Build/type-check only | Playwright for key flows (sign-up, booking, payment) |
| Error tracking | Logs only | Sentry (frontend + backend) |
| Scheduler | Thread inside API | Separate worker/cron if load grows |
| CSP | `unsafe-inline` scripts | Nonce-based CSP |
| International | Spec 5 is a draft | Build after approval (USD, countries) |
| Legal text | 9 "[… to be filled in]" gaps | Fill in company name, address, email before launch |
| Monitoring | `/health` only | Uptime monitor + alerts |
| Backups | Render's daily backups | Test a restore once |
| Admin security | Password only | Add 2FA for admins |
