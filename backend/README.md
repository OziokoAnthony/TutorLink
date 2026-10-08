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
- **Tutor work emails.** Registration assigns each tutor a work email: initial of the surname, a
  dot, the first name, at `TUTOR_EMAIL_DOMAIN` (`o.anthony@tutorlink.com`; the next Anthony Ozioko
  gets `o.anthony2@…`). It's returned as `user.work_email` and is their only login: logging in with
  their personal email gets a 401 naming the work email. Tutors don't send a `password` when they
  register: TutorLink generates one and emails it, with the work email, to their personal email
  (nothing is ever sent to the work email). `PUT /auth/me/password` changes it. Nobody can register
  with an address at that domain. Parents and admins choose a password and log in with their own email.
- The same booking or lesson comes back in a different shape for the parent, the tutor and the
  admin, so each side sees only its own fee figures (spec 1, R1).
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
- **Reading reviews:** `GET /v1/tutors/{tutor_id}/reviews` is public and shows each parent's first
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
