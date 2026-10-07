# TutorLink Backend

REST API for TutorLink, a home tutoring platform where Nigerian parents find vetted tutors,
book recurring weekly sessions, and pay monthly for parent-confirmed lessons.

Stack: Python 3.11 · FastAPI · SQLModel · PostgreSQL 16 · Alembic · uv · Docker.
See `CLAUDE.md` for the full spec. This is the `backend/` folder of the TutorLink repository;
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

There is one migration per build step (`alembic/versions/0001_auth.py` … `0006_webhook_events.py`).

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
- **Tutor ids in URLs are user ids.** In `/v1/tutors/{tutor_id}`, `/vet` and `/schedule`, and in
  `tutor_id` on schedules and invoice items, the id is `users.id`. `GET /v1/tutors` returns it
  as `user_id`.
- Tutors register with `full_name`, `area` and `rate_per_session`. Their profile starts as
  `pending` and doesn't appear in `GET /v1/tutors` until an admin approves it.
- Parents can book a tutor only if the tutor is approved and has added that subject and level
  to their profile.
- Tutors can log a session only for today or a past date, using Nigerian time (WAT, UTC+1).
- The session date must fall on the schedule's weekday.
- On a cancelled schedule, tutors can still log sessions up to the day it was cancelled, but not
  after.
- `GET /health` is an unversioned copy of `GET /v1/health`, for load balancers and container
  healthchecks.

## Tutor ratings

- **Rate a tutor:** `PUT /v1/tutors/{tutor_id}/reviews` with `{ "rating": 1-5, "comment": "..." }`.
  - Parents only, and only after at least one confirmed session with that tutor.
  - Each parent has one review per tutor; rating again updates it.
- **Ratings on tutor profiles:** `GET /v1/tutors` and `GET /v1/tutors/{tutor_id}` include
  `average_rating` (null until the first rating) and `rating_count`.
- **Sorting:** `GET /v1/tutors?sort=rating` lists the best-rated tutors first. More ratings break
  ties, and unrated tutors come last.
- **Reading reviews:** `GET /v1/tutors/{tutor_id}/reviews` is public and shows each parent's first
  name only.
- **Rating prompts:**
  - `GET /v1/auth/me` returns `tutors_to_rate` for parents.
  - Parents get a "How was your lesson with …?" email after their first confirmed session with
    a tutor.

## Payments (Paystack)

`POST /v1/invoices/{id}/pay` starts a Paystack transaction and returns its `authorization_url`.
Paystack then calls `POST /v1/webhooks/payment`:

- The webhook signature is checked against `PAYSTACK_WEBHOOK_SECRET`. Paystack signs with your
  secret key, so set this to the same value as `PAYSTACK_SECRET_KEY`. While it is empty or still
  the `.env.example` placeholder, every webhook is rejected with 503.
- Before an invoice is marked paid, the transaction is re-checked with Paystack's Verify Transaction
  API (status, amount and currency must match). If Paystack can't be reached the webhook returns 502
  and isn't recorded, so Paystack's retry is processed.
- Each event is processed once:
  - If an `X-Paystack-Event-Id` header is present, it identifies the event.
  - Otherwise the event is identified by `<event>:<transaction id>`.
- On `charge.failed` for the invoice's latest payment attempt, a pending invoice is marked
  `failed`. The parent can then pay again, which sets it back to `pending`. Only a paid invoice
  is refused, with 409.
- On `charge.success`, the invoice is marked paid only if the amount and currency match it.
  - The invoice is found by its Paystack reference.
  - If that reference doesn't match, it falls back to the `invoice_id` in the transaction
    metadata. This handles a parent who started more than one payment attempt.

## Emails (Resend)

Emails go out for the 8 triggers listed in `CLAUDE.md`. While `RESEND_API_KEY` is still the
`.env.example` placeholder, emails are only logged, not sent. A failed send is logged and never
fails the request.

## URLs

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Health | http://localhost:8000/v1/health |
| Docs | http://localhost:8000/docs |
| Adminer | http://localhost:8080 (server: `db`, user/pass: `postgres`) |
