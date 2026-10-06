# TutorLink

Home tutoring platform for Nigerian parents: find vetted tutors, book recurring weekly lessons,
and pay monthly, only for lessons the parent confirmed.

| Folder | What | Stack |
|---|---|---|
| [`backend/`](backend/) | REST API at `http://localhost:8000/v1` | FastAPI, SQLModel, PostgreSQL 16, Alembic, Paystack, Resend |
| [`frontend/`](frontend/) | Web app at `http://localhost:3000` | Next.js 14, TypeScript, Tailwind, shadcn/ui |

Each app has its own `README.md` (how to run it) and `CLAUDE.md` (its spec).

## Data model (ERD)

PostgreSQL schema, from the SQLModel tables in `backend/app/domains/*/models.py`.
Every table except `tutor_subjects`, `invoice_items` and `webhook_events` also has `created_at` and `updated_at`.

```mermaid
erDiagram
    users ||--o| parent_profiles : "has (parent)"
    users ||--o| tutor_profiles : "has (tutor)"
    users |o--o{ tutor_profiles : "vets (admin)"
    tutor_profiles ||--o{ tutor_subjects : teaches
    users ||--o{ schedules : "books (parent)"
    users ||--o{ schedules : "is booked (tutor)"
    schedules ||--o{ sessions : generates
    users |o--o{ sessions : "logs (tutor)"
    users |o--o{ sessions : "confirms (parent)"
    users ||--o{ invoices : "is billed (parent)"
    invoices ||--|{ invoice_items : contains
    sessions ||--o| invoice_items : "billed as"
    users ||--o{ invoice_items : "earns (tutor)"
    users ||--o{ tutor_reviews : "writes (parent)"
    users ||--o{ tutor_reviews : "receives (tutor)"

    users {
        uuid id PK
        string email UK
        string password_hash
        user_role role "parent | tutor | admin"
        bool is_active
    }
    parent_profiles {
        uuid id PK
        uuid user_id FK,UK
        string full_name
        string phone
        text address
    }
    tutor_profiles {
        uuid id PK
        uuid user_id FK,UK
        string full_name
        string phone
        text bio
        string area
        decimal rate_per_session
        vetting_status vetting_status "pending | approved | rejected"
        text vetting_note
        uuid vetted_by FK "admin user"
        timestamptz vetted_at
    }
    tutor_subjects {
        uuid id PK
        uuid tutor_profile_id FK
        string subject
        education_level level "primary | junior_secondary | senior_secondary"
        timestamptz created_at
    }
    schedules {
        uuid id PK
        uuid tutor_id FK
        uuid parent_id FK
        smallint day_of_week "0=Mon ... 6=Sun"
        time start_time
        time end_time
        string subject
        education_level level
        bool is_active
    }
    sessions {
        uuid id PK
        uuid schedule_id FK "unique with session_date"
        date session_date
        text topic_covered
        text homework
        session_status status "scheduled | logged | confirmed | cancelled"
        uuid logged_by FK
        timestamptz logged_at
        uuid confirmed_by FK
        timestamptz confirmed_at
    }
    invoices {
        uuid id PK
        uuid parent_id FK "unique with month + year"
        smallint billing_month
        smallint billing_year
        int total_sessions
        decimal subtotal
        decimal commission_rate
        decimal commission_amount
        decimal total_amount
        string paystack_reference
        invoice_status status "pending | paid | failed"
        timestamptz paid_at
    }
    invoice_items {
        uuid id PK
        uuid invoice_id FK
        uuid session_id FK,UK
        uuid tutor_id FK
        date session_date
        decimal amount
        decimal commission_amount
        timestamptz created_at
    }
    tutor_reviews {
        uuid id PK
        uuid tutor_id FK "unique with parent_id"
        uuid parent_id FK
        smallint rating "1-5"
        text comment
    }
    webhook_events {
        uuid id PK
        string event_id UK "Paystack event, for idempotency"
        string event_type
        timestamptz processed_at
    }
```

Key rules the schema enforces:
- One profile per user: `parent_profiles.user_id` and `tutor_profiles.user_id` are unique.
- A schedule is a recurring weekly slot; each lesson is one `sessions` row, unique per `(schedule_id, session_date)`.
- A session is billed at most once (`invoice_items.session_id` is unique), and a parent gets one invoice per month (`parent_id, billing_month, billing_year`).
- One review per parent per tutor (`tutor_id, parent_id`), rating 1-5.
- `webhook_events` is standalone: it records processed Paystack events so a webhook is never applied twice.

## Run everything locally

```bash
# Backend: API, Postgres and Adminer in Docker
cd backend
cp .env.example .env              # set SECRET_KEY; add Paystack/Resend keys when you have them
docker compose up -d --build
docker compose exec app uv run alembic upgrade head
docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng

# Frontend
cd ../frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Then open http://localhost:3000.

## Tests

```bash
cd backend  && uv run pytest     # needs the db container running
cd frontend && npm run build     # type-check + lint + production build
```
