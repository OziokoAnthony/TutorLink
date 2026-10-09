# TutorLink Backend — CLAUDE.md

TutorLink is a home tutoring marketplace for Nigerian parents. This folder is the REST API
(`/v1`); the Next.js app in `../frontend/` calls it. `README.md` covers setup, API conventions,
payments and background jobs.

## What to build: the specs

The product is specified in `../specs/`, one approved spec per feature, built in order:

1. `feature-1-bookings-and-payments.md`: offers, booking requests, prepaid bank-transfer payments, hidden fees, lessons, problems and refunds, tutor payouts. **Built.**
2. `feature-2-job-posts.md`: parents post jobs with their own price, approved tutors apply, choosing one books them. **Built.**
3. `feature-3-online-lessons.md`: online or offline lessons, meeting links, recording consent, lesson recordings uploaded straight to R2. **Built.**
4. `feature-4-tutor-onboarding.md`: Google sign-in, work emails, profile pictures, NIN verification, certificates, the qualifying exam. **Built.**
5. `feature-5-international.md` (draft: location, NGN/USD, job visibility by country)

Read the spec before changing a feature it covers. Requirement ids (R1.2, R5.3…) are the shared
vocabulary: cite them in docstrings and tests where a rule is enforced. Each spec's acceptance
criteria become tests.

## Stack

Python 3.11 · FastAPI · SQLModel · PostgreSQL 16 · Alembic · uv · Paystack (Dedicated Virtual
Accounts, Transfers) · Resend · pytest.

## Architecture

Every domain in `app/domains/<name>/` has three layers:

- `router.py`: HTTP only: routes, auth guards (`require_roles`), response models.
- `service.py`: all business logic and DB access. Other domains are reached through their
  `service` module.
- `models.py`: SQLModel tables and request/response schemas.

Add a new router to the loop in `app/api.py` and its tables to `app/db/models.py`, and add one
Alembic migration per spec or build step in `alembic/versions/`.

## Conventions

- **Time.** Read the current time through `app.core.clock.now()`, so tests can move the clock;
  timestamps through `app.db.base.utcnow()` are fine for bookkeeping. Lesson dates and times are
  WAT (`clock.WAT`, `clock.at_wat`); store instants as aware UTC datetimes.
- **Money.** `Decimal` naira everywhere, rounded with `clock.money`, and `clock.to_kobo` only at
  the Paystack boundary. API JSON carries money as decimal strings.
- **Who sees what (spec 1, R1).** A booking or lesson has one response model per reader:
  `…ParentView`, `…TutorView`, `…AdminView`. A field a reader must not see is absent from its
  model, so the API enforces visibility and the frontend only shows what it gets. Parents see P and
  their own total, never a fee rate or tutor earning; tutors see P, their fee and earning, never
  the parent total or parent fee. A tutor's full bank account number appears only in admin models.
- **Snapshots.** A booking copies price, subjects and slots at request time and freezes both fee
  rates at accept; lessons copy their price, parent price and earning when created. Later changes
  to offers or `platform_fees` never touch existing bookings.
- **Parent balance.** Move money only with `payments.add_entry` inside a `lock_parent` lock: the
  balance is the sum of `wallet_entries`, and each entry's unique `reference` makes it idempotent.
- **Paystack.** Call it only through `app/core/paystack.py`. Webhooks are verified (HMAC), recorded
  once in `webhook_events` in the same transaction as their effect, and deposits are re-verified
  with Paystack before crediting.
- **Notifications.** `notifications.notify(...)` records the in-app notification and queues the
  email, which is sent only after the transaction commits. Every R7 event goes through it.
- **Time-based rules** (expiry, release, due periods, flags, payable earnings) are functions in the
  domain services, called by `app/jobs.py`. Write them as idempotent catch-up passes over `now`.
- **Ids.** `tutor_id` and `parent_id` are always `users.id`, in URLs and in tables.
- **Accounts (spec 4 R0, R1).** Parents and tutors sign up the same way: any email and a chosen
  password (`POST /auth/register`), or Google (`POST /auth/google/register`, signed in at once).
  `users.email` is everyone's login and where every email goes. Google ID tokens are verified only in
  `app/core/google.py`; someone who signed up with Google has `password_hash = NULL` until they use
  "Forgot password?". Admins can't use Google. Tutor work emails were removed (migration 0019).
  In tests, `helpers.register_tutor` signs up with email and `helpers.PASSWORD`;
  `helpers.google_token(email, …)` mints tokens the `google` fixture accepts, and
  `helpers.google_register` signs up through Google.
- **Password reset (spec 4 R0.7).** `password_reset_tokens` stores only a SHA-256 of each link's
  token; a link works once, for an hour, and `/auth/forgot-password` answers the same for any email.
- **Tutor onboarding (spec 4 R2, R3).** `app/domains/onboarding/` holds the checklist
  (`GET /onboarding`) and NIN verification (`POST /onboarding/nin`). Dojah is called only in
  `app/core/dojah.py`; tests answer it with `helpers.dojah` (a `FakeDojah`: `dojah.add(first, surname)`
  registers a NIN record). `nin_verifications` never holds the full NIN, the NIN record's name, its photo
  or the selfie: only last 4 digits and `security.hash_nin` (keyed by `SECRET_KEY`). A verified NIN sets
  `tutor_profiles.nin_verified_at`, which locks the tutor's name except for admins.
  `onboarding.missing_for_approval` is the one list of what approval needs; `helpers.approved_tutor`
  goes through it (picture, NIN, a verified certificate, a passed exam, then vetting).
  `helpers.verified_tutor` stops after the NIN, `helpers.certified_tutor` after the certificate,
  `helpers.ready_tutor` after the exam.
- **Certificates (spec 4 R4).** `app/domains/certificates/`: files are private in storage and reach only
  their tutor and admins as short-lived links. A WAEC/NECO checker PIN is stored with `security.encrypt`
  and erased when an admin reviews the certificate. `CertificateType` is shared with job posts'
  minimum certificate (one `certificate_type` enum).
- **Qualifying exam (spec 4 R5).** `app/domains/exam/`. Claude is called only in `app/core/claude.py`
  (model `EXAM_MODEL`, structured JSON output, `fallbacks: "default"` for refusals): one call writes a
  batch of questions, a second answers each without the key, and only agreeing questions are kept.
  Generation runs in a background thread (`exam.request_generation`), started on demand when an attempt
  can't be filled and by `jobs.run_once` (`top_up_bank`, outside `run_all`). In tests the `claude` fixture
  fakes Claude (`helpers.FakeClaude`, whose right options end in `helpers.CORRECT`) and runs generation at
  once; `helpers.take_exam(client, tutor, right=N)` takes a whole attempt.
- **Sessions.** Login responses set the token as an httpOnly cookie (`deps.SESSION_COOKIE`, SameSite=Lax,
  `COOKIE_DOMAIN` in production); `get_current_user` also accepts a Bearer header (API clients, tests).
  A cookie-authenticated POST/PUT/PATCH/DELETE needs `X-Requested-With: TutorLink` (CSRF). Tokens carry
  `users.token_version`; `auth.service._end_all_sessions` raises it on a password change or reset. Admin
  tokens last `ADMIN_TOKEN_EXPIRE_MINUTES` (4 h). The test `client` keeps no cookies; use `browser` for them.
- **Rate limits.** `app/domains/auth/limits.py`: rules per email and per IP on login failures, sign-ups,
  Google sign-in and reset emails, counted in `rate_limit_hits`. Off in tests (`RATE_LIMITS_ENABLED`) except
  `tests/test_limits.py`.
- **Subjects.** Only `app/domains/tutors/subjects.py` subjects are accepted for offers and jobs, because they
  reach Claude's exam prompt (where they're also fenced as data). The frontend list in `lib/format.ts` must
  match (`tests/test_subjects.py`).
- **Keys.** `SECRET_KEY` signs tokens; `FILE_SIGNING_KEY`, `FIELD_ENCRYPTION_KEY` and `NIN_HASH_KEY` do their own
  jobs (derived from `SECRET_KEY` while unset in development; required and distinct in production).
- **Errors.** Raise `HTTPException` with a plain-English `detail` the frontend can show as is:
  404 when it doesn't exist, 403 for the wrong role or someone else's resource, 409 for a state
  conflict, 422 for invalid input.

## Guardrails

- `password_hash` stays out of every response model.
- `GET /tutors` and `GET /tutors/{id}` return approved tutors only, and with `/tutors/{id}/schedule` and `/reviews` need a logged-in parent or admin (`deps.can_see_tutors`): anonymous visitors and tutors can't browse tutors.
- A job post reaches tutors only once an admin approves it (spec 2 R1.4); `helpers.post_job` approves, `helpers.submit_job` leaves it pending.
- A forged, duplicate or unverified webhook leaves the database unchanged.
- An earning is paid at most once; a failed transfer makes it payable again.
- Placeholder secrets (`is_placeholder`) are treated as unset: the app refuses a placeholder
  `SECRET_KEY`, rejects webhooks without a real secret, and logs emails instead of sending them.

## Running and testing

The database is the `db` service of `docker-compose.yml`, published on host port **5435**
(5432–5434 are taken on this machine). Other projects' Postgres containers may be running; they
are not this one.

```bash
docker compose up -d db          # TutorLink's Postgres only
uv run pytest                    # ~3 min; creates and migrates a separate tutorlink_test database
uv run python -m app.jobs        # one pass of the background jobs
```

Fixtures in `tests/conftest.py`: `client`, `db`, `paystack` (a `FakePaystack`; no network),
`clock` (a `FakeClock` with `travel(hours=…)`), `outbox` (sent emails) and `admin_headers`.
`tests/helpers.py` builds the states a test starts from (`approved_tutor`, `accepted_booking`,
`paid_booking`, `completed_lesson`, `deposit`, `transfer_event`…); reuse and extend those.
Drive time-based rules with `clock.travel(...)` then `helpers.run_jobs(db, clock)`.
