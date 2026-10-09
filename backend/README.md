# TutorLink Backend

REST API for TutorLink, a home tutoring platform where Nigerian parents find vetted tutors,
book recurring weekly lessons and pay ahead by bank transfer; TutorLink pays tutors after the lessons.
What it does is specified in [`../specs/`](../specs/).

Stack: Python 3.11 · FastAPI · SQLModel · PostgreSQL 16 · Alembic · uv · Docker.
See `CLAUDE.md` for how the code is organised. This is the `backend/` folder of the TutorLink repository;
run the commands below from here. The web app is in [`../frontend`](../frontend).

## Setup

```bash
cp .env.example .env            # then set a real SECRET_KEY (32+ chars)
docker compose up --build -d    # app + postgres + adminer
docker compose exec app uv run alembic upgrade head
docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng
uv sync                         # local venv for tests
```

Postgres from Docker is published on host port **5435**: 5432 is taken by a local Windows
Postgres and 5433–5434 by WSL. Inside Docker the app reaches it at `db:5432`.

## Required settings

The API refuses to start without these (`app/core/config.py` checks them). Generate each key with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

| Setting | When | Rule |
|---|---|---|
| `SECRET_KEY` | always | 32+ characters, not the `.env.example` placeholder. Signs login tokens. |
| `DATABASE_URL` | always | The Postgres connection URL. |
| `FILE_SIGNING_KEY` | `APP_ENV=production` | Its own 32+ character key, different from `SECRET_KEY`. Signs file links. |
| `FIELD_ENCRYPTION_KEY` | `APP_ENV=production` | Its own 32+ character key, different from `SECRET_KEY`. Encrypts WAEC/NECO checker PINs. |
| `NIN_HASH_KEY` | `APP_ENV=production` | Its own 32+ character key, different from `SECRET_KEY`. Hashes NINs. |

`docker compose` also refuses to start without `POSTGRES_PASSWORD` in `.env`.

Don't change the three production keys once real data exists: a new `FILE_SIGNING_KEY` breaks file links
already handed out, a new `FIELD_ENCRYPTION_KEY` makes stored checker PINs unreadable, and a new
`NIN_HASH_KEY` lets an already-verified NIN verify a second account.

The API starts without these, but set them in production:

- `COOKIE_DOMAIN`: the domain the site and the API share (e.g. `tutorlink.ng`). Without it, the site's
  middleware can't see the login cookie, and logged-in users are sent back to the login page.
- `TRUST_PROXY_HEADERS=true`, only behind a proxy or CDN (Render, Cloudflare). Without it, rate limits count
  the proxy's address, so one person's failed logins can block everyone.
- `BASE_URL` and `FRONTEND_URL` with `https://`: the login cookie is then marked Secure and HSTS is sent.
- Paystack, Resend, Google, Dojah and Anthropic keys: without them, those features are off (payments,
  emails, Google sign-in, NIN checks, exam generation).
- The `STORAGE_*` bucket settings: without them, uploaded files go to a local folder, which is for
  development only.

## Admin accounts

Nobody can register as an admin. Create admins with the CLI script; it prompts for the
password when `--password` is omitted:

```bash
docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng
```

## Migrations

Migrations are in `alembic/versions/`, one per build step or spec.

```bash
docker compose exec app uv run alembic upgrade head
# From the host, point Alembic at the published port instead of the `db` hostname:
ALEMBIC_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5435/tutorlink_db uv run alembic check
```

## Tests

```bash
uv run pytest    # requires the db container to be running
```

The tests create a separate `tutorlink_test` database. They run every migration down and back
up, then truncate the tables before each test. Emails and Paystack calls are faked.

## API conventions

- All routes are under `/v1`. Interactive docs are at `/docs`.
- Send `Authorization: Bearer <token>`. The token comes from `POST /v1/auth/login`.
- **Tutor ids in URLs are user ids.** In `/v1/tutors/{tutor_id}` and everywhere a `tutor_id` or
  `parent_id` appears, the id is `users.id`. `GET /v1/tutors` returns it as `user_id`.
- Money is sent and returned as decimal strings in naira (`"5000.00"`).
- Lesson dates and times are Nigerian local time (WAT, UTC+1, no daylight saving).
- Tutors register with `first_name`, `surname` and at least one offer (subjects, level, weekly
  windows, price). Their profile starts as `pending` and doesn't appear in `GET /v1/tutors` until an
  admin approves it.
- **Accounts.** Parents and tutors sign up the same way: `POST /v1/auth/register` with any email and
  a chosen password, or `POST /v1/auth/google/register` with a Google ID token (signed in at once).
  Everyone logs in with their email (`/auth/login`) or Google (`/auth/google/login`, not for admins),
  and every email goes to that address. `PUT /auth/me/password` changes a password. There are no
  TutorLink work emails any more (removed in migration 0019).
- **Seeing tutors.** `GET /v1/tutors`, `/tutors/{id}`, `/tutors/{id}/schedule` and `/reviews` need a
  logged-in parent or admin.
- The same booking or lesson comes back in a different shape for the parent, the tutor and the
  admin, so each side sees only its own fee figures (spec 1, R1).
- **Job posts (spec 2).** Parents `POST /v1/jobs` with their own price per lesson. The job is `pending`
  until an admin approves it (`PATCH /v1/admin/jobs/{id}`, queue at `GET /v1/admin/jobs?status=pending`);
  an edit sends it back for review. Approved tutors browse open jobs (`GET /v1/jobs?subject=&level=&mode=&area=`), apply once
  (`POST /v1/jobs/{id}/apply`) and can withdraw while the job is open. The parent lists applicants
  (`GET /v1/jobs/{id}/applications`) and chooses one
  (`POST /v1/jobs/{id}/applications/{application_id}/choose`), which creates a booking already
  awaiting payment (`bookings.job_id` points back at the job). The job is then `ongoing`. It becomes
  `completed` when that booking ends, or `open` again if the booking closes before it was paid.
  Tutors see the parent's first name and picture only, never their surname or contact details.
- `GET /health` is an unversioned copy of `GET /v1/health`, for load balancers and container
  healthchecks.

## Background jobs

Request expiry, unpaid-booking release, next billing periods, paying due periods from balances,
payment reminders, missing-report flags and payable earnings are time-based. `app/jobs.py` runs
them every `SCHEDULER_INTERVAL_SECONDS` inside the API process (a Postgres advisory lock keeps it to
one process). Set `RUN_SCHEDULER=false` to turn it off, and run one pass by hand with:

```bash
uv run python -m app.jobs
```

## Tutor ratings

- **Rate a tutor:** `PUT /v1/tutors/{tutor_id}/reviews` with `{ "rating": 1-5, "comment": "..." }`.
  - Parents only, and only after at least one completed lesson with that tutor.
  - Each parent has one review per tutor; rating again updates it.
- **Ratings on tutor profiles:** `GET /v1/tutors` and `GET /v1/tutors/{tutor_id}` include
  `average_rating` (null until the first rating) and `rating_count`.
- **Sorting:** `GET /v1/tutors?sort=rating` lists the best-rated tutors first. More ratings break
  ties, and unrated tutors come last.
- **Reading reviews:** `GET /v1/tutors/{tutor_id}/reviews` is for logged-in parents and admins and shows each parent's first
  name only.
- **Rating prompts:** `GET /v1/auth/me` returns `tutors_to_rate` for parents.

## Payments (Paystack)

There are no card payments. Each parent gets a Paystack Dedicated Virtual Account (their own
account number) the first time one of their bookings is accepted. Paystack reports every event to
`POST /v1/webhooks/payment`:

- The signature is checked against `PAYSTACK_WEBHOOK_SECRET`. Paystack signs with your secret key,
  so set this to the same value as `PAYSTACK_SECRET_KEY`. While it is empty or still the
  `.env.example` placeholder, every webhook is rejected with 503.
- Each event is processed once: by its `X-Paystack-Event-Id` header when present, otherwise by
  `<event>:<transaction id>`.
- **`charge.success`** is a bank transfer into a parent's account number. It is re-checked with
  Paystack's Verify Transaction API (success, NGN, same customer) and Paystack's amount is credited
  to the parent's balance. If Paystack can't be reached the webhook returns 502 and isn't recorded,
  so Paystack's retry is processed. The balance then pays any due periods, oldest first.
- **`transfer.success` / `transfer.failed` / `transfer.reversed`** settle tutor payouts (reference
  `PO-…`) and parent withdrawals (`WD-…`). A failed payout makes its earnings payable again.

Dedicated accounts and Transfers must be enabled on the Paystack account. `PAYSTACK_DVA_BANK` picks
the bank for account numbers: `test-bank` in test mode.

## Online lessons and recordings

Every booking and job is `online` or `offline`. Booking or posting an online lesson needs
`recording_consent: true`, and the time and text of the consent are stored. The tutor sets the
video call link with `PUT /v1/bookings/{id}/meeting-link` (https only). The parent sees it, and for
offline lessons the tutor sees the parent's address, only once the first period is paid.

An online lesson's report needs its recording first. Video never passes through the API:

1. `POST /v1/lessons/{id}/recording/upload` with `filename`, `content_type` and `size` returns a
   signed `upload_url`. It accepts MP4, WebM or MOV at most 2 GB, and the link is valid for 1 hour.
2. The browser `PUT`s the file to `upload_url` with that exact `Content-Type` and size.
3. `POST /v1/lessons/{id}/recording/complete` checks the stored file's type and size. The report
   checks them again.

`GET /v1/lessons/{id}/recording` returns a viewing link that expires after 15 minutes, for the
lesson's parent, its tutor and admins only. The background jobs delete recordings 90 days after the
lesson, unless a problem on that lesson is still open.

Files live in a private S3-compatible bucket (Backblaze B2 or Cloudflare R2: the `STORAGE_*` settings
in `.env.example`). Uploads go to the bucket through presigned URLs, so the bucket needs a CORS rule
allowing `PUT` (and `GET` for playback) from the frontend's origin with the `Content-Type` header.
Without a bucket, files go to `LOCAL_STORAGE_DIR` through the signed `/v1/files/...` routes
(development and tests only).

## Notifications and emails (Resend)

Every notification is stored for the in-app list (`GET /v1/notifications/me`) and emailed once the
change commits. While `RESEND_API_KEY` is still the `.env.example` placeholder, emails are only
logged, not sent. A failed send is logged and never fails the request.

## URLs

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Health | http://localhost:8000/v1/health |
| Docs | http://localhost:8000/docs |
| Adminer | http://localhost:8080 (server: `db`, user/pass: `postgres`) |
