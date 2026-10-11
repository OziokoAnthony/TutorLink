#!/bin/sh
# Render start command: bring the database up to date, then start the API. Calls the installed programs
# directly: `uv run` re-checks and recompiles every package first, which on a small instance takes long
# enough for the start to fail.
set -e

echo "Running migrations..."
/app/.venv/bin/alembic upgrade head

echo "Starting server..."
exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
