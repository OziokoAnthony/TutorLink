# TutorLink Backend — CLAUDE.md
# Read this file before doing anything. Follow every instruction exactly.

---

## WHAT WE ARE BUILDING

TutorLink is a home tutoring platform where Nigerian parents find vetted tutors,
book recurring weekly sessions, and pay monthly — only for lessons that were confirmed
by the parent.

This repo is the **backend only** (REST API).
The frontend (Next.js) is a separate repo that calls this API.

---

## STACK

```
Language:         Python 3.11
Framework:        FastAPI
ORM:              SQLModel (SQLAlchemy + Pydantic)
Database:         PostgreSQL 16
Migrations:       Alembic
Auth:             PyJWT + passlib[bcrypt]
Payments:         Paystack (test mode)
Email:            Resend
Package manager:  uv
Containers:       Docker + docker-compose
Testing:          pytest + httpx
```

---

## ARCHITECTURE PATTERN

Every domain follows this exact 3-layer pattern. Never deviate:
```
router.py  →  service.py  →  models.py
(HTTP)        (Business)      (Data)
```
- `router.py`  — HTTP endpoints, request/response schemas, auth guards
- `service.py` — ALL business logic, DB reads/writes, cross-domain calls
- `models.py`  — SQLModel tables + Pydantic DTOs (request and response shapes)

---

## BASE MODEL (ALL tables inherit this)

```python
class BaseUUIDModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Rules:
- ALWAYS use `datetime.now(timezone.utc)` — NEVER `datetime.utcnow()`
- All timestamps are timezone-aware (TIMESTAMPTZ in PostgreSQL)

---

## FOLDER STRUCTURE

```
tutorlink-backend/
├── app/
│   ├── main.py              ← FastAPI app, CORS, X-Request-ID middleware, router mount
│   ├── api.py               ← Master /v1 router (includes all domain routers)
│   ├── core/
│   │   ├── config.py        ← Settings class loaded from .env (pydantic-settings)
│   │   ├── security.py      ← get_password_hash(), verify_password(), create_access_token()
│   │   └── deps.py          ← get_current_user(), require_roles([...])
│   ├── db/
│   │   ├── base.py          ← BaseUUIDModel
│   │   └── session.py       ← get_session() FastAPI dependency
│   └── domains/
│       ├── auth/            ← router.py, service.py, models.py, __init__.py
│       ├── tutors/          ← router.py, service.py, models.py, __init__.py
│       ├── schedules/       ← router.py, service.py, models.py, __init__.py
│       ├── sessions/        ← router.py, service.py, models.py, __init__.py
│       ├── billing/         ← router.py, service.py, models.py, __init__.py
│       ├── notifications/   ← service.py, __init__.py (no router — internal only)
│       └── webhooks/        ← router.py, service.py, __init__.py
├── alembic/
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
└── README.md
```

---

## DATABASE TABLES

Design every table exactly as specified below. No changes.

### Table 1: `users`
```
id                UUID          PK, auto-generated
email             VARCHAR       UNIQUE, NOT NULL, stored as lowercase
password_hash     VARCHAR       NOT NULL
role              ENUM          NOT NULL — values: 'parent', 'tutor', 'admin'
is_active         BOOLEAN       DEFAULT true
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL
```

### Table 2: `parent_profiles`
```
id                UUID          PK
user_id           UUID          FK → users.id, UNIQUE
full_name         VARCHAR       NOT NULL
phone             VARCHAR       NULLABLE
address           TEXT          NULLABLE
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL
```

### Table 3: `tutor_profiles`
```
id                UUID          PK
user_id           UUID          FK → users.id, UNIQUE
full_name         VARCHAR       NOT NULL
phone             VARCHAR       NULLABLE
bio               TEXT          NULLABLE
area              VARCHAR       NOT NULL
rate_per_session  NUMERIC(10,2) NOT NULL (in Naira)
vetting_status    ENUM          DEFAULT 'pending' — values: 'pending','approved','rejected'
vetting_note      TEXT          NULLABLE
vetted_by         UUID          FK → users.id, NULLABLE
vetted_at         TIMESTAMPTZ   NULLABLE
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL
```

### Table 4: `tutor_subjects`
```
id                UUID          PK
tutor_profile_id  UUID          FK → tutor_profiles.id
subject           VARCHAR       NOT NULL (e.g. "Mathematics")
level             ENUM          NOT NULL — values: 'primary','junior_secondary','senior_secondary'
created_at        TIMESTAMPTZ   NOT NULL

UNIQUE constraint: (tutor_profile_id, subject, level)
```

### Table 5: `schedules`
```
id                UUID          PK
tutor_id          UUID          FK → users.id
parent_id         UUID          FK → users.id
day_of_week       SMALLINT      NOT NULL (0=Monday ... 6=Sunday)
start_time        TIME          NOT NULL
end_time          TIME          NOT NULL
subject           VARCHAR       NOT NULL
level             ENUM          NOT NULL (same values as tutor_subjects.level)
is_active         BOOLEAN       DEFAULT true
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL

INDEX on (tutor_id, day_of_week, is_active) for fast clash detection
```

### Table 6: `sessions`
```
id                UUID          PK
schedule_id       UUID          FK → schedules.id
session_date      DATE          NOT NULL
topic_covered     TEXT          NULLABLE
homework          TEXT          NULLABLE
status            ENUM          DEFAULT 'scheduled'
                                values: 'scheduled','logged','confirmed','cancelled'
logged_by         UUID          FK → users.id, NULLABLE
logged_at         TIMESTAMPTZ   NULLABLE
confirmed_by      UUID          FK → users.id, NULLABLE
confirmed_at      TIMESTAMPTZ   NULLABLE
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL

UNIQUE constraint: (schedule_id, session_date)
```

Session status flow:
```
scheduled → logged → confirmed
                   ↘ cancelled
```

### Table 7: `invoices`
```
id                    UUID          PK
parent_id             UUID          FK → users.id
billing_month         SMALLINT      NOT NULL (1-12)
billing_year          SMALLINT      NOT NULL (e.g. 2025)
total_sessions        INTEGER       NOT NULL
subtotal              NUMERIC(10,2) NOT NULL
commission_rate       NUMERIC(5,4)  NOT NULL (e.g. 0.1000 = 10%)
commission_amount     NUMERIC(10,2) NOT NULL
total_amount          NUMERIC(10,2) NOT NULL
paystack_reference    VARCHAR       NULLABLE
status                ENUM          DEFAULT 'pending' — values: 'pending','paid','failed'
paid_at               TIMESTAMPTZ   NULLABLE
created_at            TIMESTAMPTZ   NOT NULL
updated_at            TIMESTAMPTZ   NOT NULL

UNIQUE constraint: (parent_id, billing_month, billing_year)
```

### Table 8: `invoice_items`
```
id                UUID          PK
invoice_id        UUID          FK → invoices.id
session_id        UUID          FK → sessions.id, UNIQUE
tutor_id          UUID          FK → users.id
session_date      DATE          NOT NULL (denormalized for display)
amount            NUMERIC(10,2) NOT NULL
commission_amount NUMERIC(10,2) NOT NULL
created_at        TIMESTAMPTZ   NOT NULL
```

### Table 9: `webhook_events`
```
id                UUID          PK
event_id          VARCHAR       UNIQUE, NOT NULL (from Paystack header)
event_type        VARCHAR       NOT NULL
processed_at      TIMESTAMPTZ   NOT NULL
```

---

## ALL API ENDPOINTS

All routes are prefixed with `/v1`.

### Auth
```
POST   /auth/register         No auth    Register (role: parent or tutor in body)
POST   /auth/login            No auth    Login → JWT access token
GET    /auth/me               JWT+Any    Current user + profile
```

### Tutors
```
POST   /tutors/profile                JWT+tutor    Create or update my tutor profile
POST   /tutors/profile/subjects       JWT+tutor    Add subject+level to my profile
DELETE /tutors/profile/subjects/{id}  JWT+tutor    Remove a subject
GET    /tutors                        No auth      List APPROVED tutors only
                                                   Query params: subject, level, area, skip, limit
GET    /tutors/{id}                   No auth      Single approved tutor profile
PATCH  /tutors/{id}/vet               JWT+admin    Approve or reject a tutor
                                                   Body: { status: 'approved'|'rejected', note?: str }
GET    /admin/tutors/pending          JWT+admin    List tutors with vetting_status=pending
```

### Schedules
```
POST   /schedules             JWT+parent   Book recurring weekly slot
                                           Body: { tutor_id, day_of_week, start_time, end_time, subject, level }
                                           Run clash detection before creating
GET    /schedules/me          JWT+parent   My active schedules
DELETE /schedules/{id}        JWT+parent   Cancel schedule (own only, sets is_active=false)
GET    /tutors/{id}/schedule  JWT+Any      A tutor's booked time slots
```

### Sessions
```
POST   /sessions                   JWT+tutor    Log a session
                                                Body: { schedule_id, session_date, topic_covered, homework }
                                                Verify tutor owns the schedule
                                                session_date must be past or today
GET    /sessions/me                JWT+parent   My sessions (filter: status, month, year)
GET    /sessions/tutor/me          JWT+tutor    My sessions as tutor
PATCH  /sessions/{id}/confirm      JWT+parent   Confirm a logged session (own only)
PATCH  /sessions/{id}/cancel       JWT+parent   Cancel a session (own only)
GET    /admin/sessions             JWT+admin    All sessions
```

### Billing
```
POST   /invoices/generate     JWT+admin    Generate invoices for given month+year
                                           Body: { month: int, year: int }
                                           Only confirmed sessions count
                                           Skip parent if invoice already exists for that month
GET    /invoices/me           JWT+parent   My invoices
GET    /invoices/{id}         JWT+parent   Invoice detail + line items
POST   /invoices/{id}/pay     JWT+parent   Initiate Paystack payment
                                           Initialize Paystack transaction
                                           Store paystack_reference on invoice
                                           Return Paystack authorization_url
```

### Webhooks
```
POST   /webhooks/payment      HMAC-SHA512  Paystack payment webhook
                                           1. Read raw bytes BEFORE parsing JSON
                                           2. Verify X-Paystack-Signature header → 401 if invalid
                                           3. INSERT INTO webhook_events ON CONFLICT DO NOTHING
                                           4. If conflict → return 200 silently (already processed)
                                           5. Find invoice by paystack_reference
                                           6. Set invoice.status='paid', invoice.paid_at=now()
                                           7. Send payment confirmation email via Resend
```

### System
```
GET    /health                No auth    { "status": "ok", "db": "connected" }
                                         Test DB connection with SELECT 1
```

---

## BUSINESS RULES

Implement every rule below as a guard clause in the relevant `service.py`.
These are non-negotiable.

1. Store email as lowercase. Uniqueness check is case-insensitive.
2. A tutor with `vetting_status != 'approved'` MUST NOT appear in GET /tutors.
3. Clash detection before creating a schedule:
   ```sql
   SELECT 1 FROM schedules
   WHERE tutor_id = :tutor_id
     AND day_of_week = :day_of_week
     AND is_active = true
     AND start_time < :new_end_time
     AND end_time > :new_start_time
   LIMIT 1
   ```
   If any row returned → raise HTTP 409: "Tutor already has a session at this time."
4. A session can only be logged by the tutor assigned to that schedule → 403 otherwise.
5. A tutor cannot log the same (schedule_id + session_date) twice → 409.
6. A session can only be confirmed by the parent who owns the schedule → 403 otherwise.
7. Only sessions with `status = 'confirmed'` count in invoice generation.
8. Only one invoice per (parent_id, billing_month, billing_year). Skip silently if exists.
9. An invoice can only be paid if `status = 'pending'` → 409 if already paid.
10. A parent can only cancel/view their own schedules → 403 otherwise.
11. Commission is calculated and stored at invoice generation time. Never recalculate later.
12. Response schemas MUST NEVER include `password_hash`.

---

## CLASH DETECTION — WORKED EXAMPLES

New slot: start=15:00, end=16:00
```
Existing:  14:30 – 15:30   → CLASH   (14:30 < 16:00 AND 15:30 > 15:00)
Existing:  15:00 – 16:00   → CLASH   (exact match)
Existing:  15:30 – 16:30   → CLASH   (15:30 < 16:00 AND 16:30 > 15:00)
Existing:  14:00 – 16:30   → CLASH   (contains the new slot)
Existing:  14:00 – 15:00   → OK      (ends exactly when new starts — no overlap)
Existing:  16:00 – 17:00   → OK      (starts exactly when new ends — no overlap)
```

---

## BILLING LOGIC

`POST /invoices/generate` with `{ month: 10, year: 2025 }`:

1. Get all unique parent_ids who have confirmed sessions in Oct 2025
2. For each parent:
   a. Find all sessions WHERE:
      - schedule.parent_id = parent.id
      - session.session_date BETWEEN 2025-10-01 AND 2025-10-31
      - session.status = 'confirmed'
   b. If no confirmed sessions → skip (do not create invoice)
   c. If invoice already exists for (parent_id, month=10, year=2025) → skip
   d. Create Invoice:
      - subtotal = SUM of tutor rate_per_session for each session
      - commission_amount = subtotal × COMMISSION_RATE (from env)
      - total_amount = subtotal (parent pays full amount)
      - commission_rate = stored as decimal (e.g. 0.1000)
   e. Create one InvoiceItem per confirmed session
   f. Send invoice email to parent via Resend

---

## ENVIRONMENT VARIABLES (.env.example)

```env
APP_ENV=development
SECRET_KEY=your_minimum_32_character_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/tutorlink_db
ALEMBIC_DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/tutorlink_db

PAYSTACK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PAYSTACK_PUBLIC_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PAYSTACK_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FROM_EMAIL=noreply@tutorlink.ng

COMMISSION_RATE=0.10
```

---

## EMAILS (via Resend)

| Trigger | To | Subject |
|---|---|---|
| Tutor registers | Tutor | "We received your application" |
| Admin approves tutor | Tutor | "You're approved! Welcome to TutorLink" |
| Admin rejects tutor | Tutor | "Update on your TutorLink application" |
| Schedule created | Parent + Tutor | "New session booked: [Subject] every [Day]" |
| Schedule cancelled | Parent + Tutor | "Session cancelled" |
| Tutor logs session | Parent | "Please confirm your [Subject] session on [Date]" |
| Invoice generated | Parent | "Your TutorLink invoice for [Month Year] is ready" |
| Payment confirmed | Parent | "Payment received — thank you!" |

---

## DOCKER SETUP

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db]

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: tutorlink_db
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  adminer:
    image: adminer
    ports: ["8080:8080"]
    depends_on: [db]

volumes:
  postgres_data:
```

---

## PYTEST TESTS — WRITE THESE FOR EVERY DOMAIN

### Auth
- Register as parent → 201
- Register as tutor → 201, vetting_status=pending
- Register duplicate email → 409
- Login correct credentials → 200, token returned
- Login wrong password → 401
- GET /auth/me with valid token → 200
- GET /auth/me with no token → 401
- password_hash never in any response

### Tutors
- Unapproved tutor not in GET /tutors
- Admin approves → tutor appears in GET /tutors
- Admin rejects → tutor stays hidden, vetting_note set
- Non-admin calls PATCH /tutors/{id}/vet → 403

### Schedules
- Parent books valid slot → 201
- Parent books clashing slot same tutor → 409
- Back-to-back slots (no overlap) → 201 allowed
- Parent cancels own schedule → 200
- Parent cancels another parent's schedule → 403
- Tutor tries to create schedule → 403

### Sessions
- Tutor logs session → 201, status=logged
- Tutor logs same schedule+date twice → 409
- Tutor logs for schedule they don't own → 403
- Parent confirms own logged session → 200, status=confirmed
- Parent confirms another parent's session → 403

### Billing
- 3 confirmed + 1 logged + 1 cancelled → invoice has 3 items only
- Generate invoice twice same month → second call skips, no duplicate
- Invoice total equals sum of tutor rates
- Commission stored correctly

### Webhooks
- Valid HMAC + charge.success → invoice.status=paid
- Invalid HMAC → 401
- Duplicate event_id → 200 silently

---

## BUILD ORDER

```
Step 1:  Scaffold (folders, Docker, Alembic, base model, health endpoint)
         Verify: docker-compose up → GET /health returns 200

Step 2:  Auth domain + migration + tests
Step 3:  Tutors domain + migration + tests
Step 4:  Schedules domain + migration + tests
Step 5:  Sessions domain + migration + tests
Step 6:  Billing domain + migration + tests
Step 7:  Webhooks domain + tests
Step 8:  Notifications (Resend emails)
```

---

## NEVER ALLOWED

- Unapproved tutor in GET /tutors ❌
- Unconfirmed session on an invoice ❌
- Parent confirming another parent's session ❌
- Invalid HMAC webhook processed ❌
- Same Paystack event_id processed twice ❌
- Tutor logging same session_date twice ❌
- Schedule created with tutor clash ❌
- Invoice generated twice same parent + month ❌
- password_hash in any API response ❌

---

## ADDENDUM: TUTOR RATINGS (added after the original spec)

Domain: `app/domains/reviews/` (router.py, service.py, models.py). Migration: `0007_tutor_reviews`.

### Table 10: `tutor_reviews`
```
id                UUID          PK
tutor_id          UUID          FK → users.id
parent_id         UUID          FK → users.id
rating            SMALLINT      NOT NULL, CHECK 1–5
comment           TEXT          NULLABLE
created_at        TIMESTAMPTZ   NOT NULL
updated_at        TIMESTAMPTZ   NOT NULL

UNIQUE constraint: (tutor_id, parent_id)
```

### Endpoints
```
PUT    /tutors/{id}/reviews   JWT+parent   Create or update my rating of this tutor
                                           Body: { rating: 1-5, comment?: str }
GET    /tutors/{id}/reviews   No auth      Reviews of an APPROVED tutor (skip, limit)
                                           Shows parent's first name only
GET    /tutors?sort=rating    No auth      Best average first, more ratings break ties, unrated last
```
`GET /tutors` and `GET /tutors/{id}` include `average_rating` (2 dp, null if unrated) and `rating_count`.
`GET /auth/me` for a parent includes `tutors_to_rate`.

### Rules
13. One review per (parent, tutor). Rating again updates it. Every parent counts once in the average.
14. A parent can only rate a tutor after at least one CONFIRMED session with them → 403 otherwise.
15. After a parent's FIRST confirmed session with a tutor, if they haven't rated that tutor yet,
    send email: "How was your lesson with [Tutor]?"

---

## ADDENDUM: FRONTEND SUPPORT (added for tutorlink-frontend)

All additive; no existing field or endpoint changed.

```
GET    /schedules/tutor/me    JWT+tutor    My active schedules as tutor (for logging sessions)
```
- `ScheduleRead` also returns `tutor_name`, `parent_name`.
- `SessionRead` also returns `subject`, `level`, `tutor_id`, `tutor_name`, `parent_name` (from its schedule).
- `POST /invoices/generate` response also returns `parents_without_sessions` (active parents with no
  confirmed sessions that month), and each invoice includes `parent_name`.
- Paystack `callback_url` = `{FRONTEND_URL}/dashboard/parent/invoices?invoice={id}`.
