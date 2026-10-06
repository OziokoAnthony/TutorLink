# TutorLink

Home tutoring platform for Nigerian parents: find vetted tutors, book recurring weekly lessons,
and pay monthly, only for lessons the parent confirmed.

| Folder | What | Stack |
|---|---|---|
| [`backend/`](backend/) | REST API at `http://localhost:8000/v1` | FastAPI, SQLModel, PostgreSQL 16, Alembic, Paystack, Resend |
| [`frontend/`](frontend/) | Web app at `http://localhost:3000` | Next.js 14, TypeScript, Tailwind, shadcn/ui |

Each app has its own `README.md` (how to run it) and `CLAUDE.md` (its spec).

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
