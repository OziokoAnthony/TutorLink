# TutorLink

Home tutoring platform for Nigerian parents: find vetted tutors, book recurring weekly lessons,
and pay ahead by bank transfer. TutorLink pays tutors after the lessons. What the product does is
specified in [`specs/`](specs/).

| Folder | What | Stack |
|---|---|---|
| [`backend/`](backend/) | REST API at `http://localhost:8000/v1` | FastAPI, SQLModel, PostgreSQL 16, Alembic, Paystack, Resend |
| [`frontend/`](frontend/) | Web app at `http://localhost:3000` | Next.js 14, TypeScript, Tailwind, shadcn/ui |

Each app has its own `README.md` (how to run it) and `CLAUDE.md` (how to work on it).

## Data model (ERD)

PostgreSQL schema, from the SQLModel tables in `backend/app/domains/*/models.py` (key columns only).
Money is `NUMERIC` naira; times are `timestamptz`, and lesson dates and times are Nigerian local time (WAT).

```mermaid
erDiagram
    users ||--o| parent_profiles : "has (parent)"
    users ||--o| tutor_profiles : "has (tutor)"
    users ||--o{ tutor_offers : "offers (tutor)"
    tutor_offers ||--|{ tutor_offer_subjects : covers
    tutor_offers ||--|{ tutor_offer_windows : "available in"
    users ||--o| tutor_bank_accounts : "is paid into (tutor)"
    users ||--o{ bookings : "requests (parent) / teaches (tutor)"
    tutor_offers ||--o{ bookings : "booked from"
    bookings ||--|{ booking_slots : "meets in"
    bookings ||--o{ booking_periods : "billed in"
    booking_periods ||--o{ lessons : "pays for"
    lessons ||--o| lesson_issues : "has problem"
    payouts ||--o{ lessons : "pays earnings of"
    users ||--o{ payouts : "receives (tutor)"
    users ||--o| virtual_accounts : "pays into (parent)"
    users ||--o{ wallet_entries : "balance of (parent)"
    booking_periods ||--o| wallet_entries : "paid by"
    refunds ||--o| wallet_entries : "credited by"
    withdrawals ||--o{ wallet_entries : "debited by"
    bookings ||--o{ refunds : "refunded on"
    users ||--o{ withdrawals : "requests (parent)"
    users ||--o{ tutor_reviews : "writes (parent) / gets (tutor)"
    users ||--o{ notifications : receives

    tutor_offers {
        uuid tutor_id FK
        level level
        decimal price "agreed price P per lesson"
        bool is_active "false once removed"
    }
    bookings {
        uuid parent_id FK
        uuid tutor_id FK
        uuid offer_id FK
        string_array subjects
        billing_period billing_period "daily | weekly | monthly"
        decimal price "P, copied at request time"
        decimal parent_fee_rate "S, frozen at accept"
        decimal tutor_fee_rate "T, frozen at accept"
        booking_status status "requested | accepted | active | paused | ended | declined | expired | released | cancelled"
    }
    booking_periods {
        uuid booking_id FK "unique with starts_on"
        date starts_on
        date ends_on
        decimal amount "what the parent pays"
        timestamptz due_at "24 h before first lesson"
        period_status status "due | paid | missed | expired | void"
    }
    lessons {
        uuid booking_id FK "unique with starts_at"
        uuid period_id FK
        timestamptz starts_at
        lesson_status status "confirmed | reported | completed | disputed | flagged | refunded | cancelled"
        decimal price "P"
        decimal parent_price "P x (1 + S)"
        decimal tutor_earning "P x (1 - T)"
        earning_status earning_status "pending | on_hold | payable | paid | void"
        timestamptz payout_due_at
        uuid payout_id FK
    }
    wallet_entries {
        uuid parent_id FK
        entry_kind kind "deposit | period_payment | refund | withdrawal | withdrawal_reversal"
        decimal amount "signed; balance = sum"
        string reference UK
    }
    platform_fees {
        int id PK "single row"
        decimal parent_fee_rate
        decimal tutor_fee_rate
    }
    webhook_events {
        string event_id UK "Paystack event, for idempotency"
    }
```

Key rules the schema enforces:
- One profile, bank account and dedicated account number per user (`user_id` / `tutor_id` / `parent_id` unique).
- A booking copies its price, subjects and slots when requested and freezes both fee rates when accepted,
  so later offer or fee changes never touch it.
- One period per booking start date, one lesson per booking start time; a lesson exists only for a paid period.
- A parent's balance is the sum of their `wallet_entries`; each entry's `reference` is unique, so a deposit
  or payment is never applied twice. `webhook_events` does the same for Paystack events.
- A lesson's earning is paid at most once (`lessons.payout_id`).
- One review per parent per tutor (`tutor_id, parent_id`), rating 1-5.

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
