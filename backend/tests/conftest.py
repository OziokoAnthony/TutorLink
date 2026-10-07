"""Tests run against a separate `tutorlink_test` database on the same Postgres as DATABASE_URL.

The schema is built by running the real Alembic migrations (down to base, then up to head),
so the migrations are exercised on every test run. Tables are truncated before each test.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel

from app.core import clock as clock_module
from app.core import paystack as paystack_client
from app.core import security
from app.core.config import settings
from app.db import models  # noqa: F401  (registers every table for TRUNCATE)
from app.db.session import get_session
from app.domains.notifications import service as notifications
from app.domains.payments import service as payments_service
from app.main import app
from tests import helpers

# bcrypt's production cost (12 rounds) makes every register/login ~0.3s; tests don't need it.
security.pwd_context.update(bcrypt__rounds=4)

ROOT = Path(__file__).resolve().parents[1]
TEST_DB_NAME = "tutorlink_test"
TEST_DATABASE_URL = make_url(settings.DATABASE_URL).set(database=TEST_DB_NAME)


def _ensure_test_database() -> None:
    server = create_engine(make_url(settings.DATABASE_URL).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    server.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database()
    alembic_cfg = Config(str(ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.render_as_string(hide_password=False))
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield test_engine
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    tables = ", ".join(table.name for table in SQLModel.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def db(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    """Captures every email instead of sending it."""
    sent: list[dict] = []
    monkeypatch.setattr(
        notifications, "send_email",
        lambda to, subject, html: sent.append({"to": to, "subject": subject, "html": html}),
    )
    return sent


@pytest.fixture(autouse=True)
def test_settings(monkeypatch, tmp_path):
    """Real-looking Paystack secrets, local file storage in a temp folder, no background scheduler,
    whatever the developer's .env holds."""
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_test_tutorlink_tests")
    monkeypatch.setattr(settings, "PAYSTACK_WEBHOOK_SECRET", "sk_test_tutorlink_tests")
    for name in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"):
        monkeypatch.setattr(settings, name, "")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "RUN_SCHEDULER", False)


@pytest.fixture(autouse=True)
def paystack(monkeypatch):
    """A fake Paystack: every API call TutorLink makes is answered here, never over the network."""
    fake = helpers.FakePaystack()
    for name in ("verify_transaction", "create_customer", "create_dedicated_account", "list_banks",
                 "resolve_account", "create_transfer_recipient", "initiate_transfer"):
        monkeypatch.setattr(paystack_client, name, getattr(fake, name))
    monkeypatch.setattr(payments_service, "_banks_cache", None)
    return fake


@pytest.fixture
def clock(monkeypatch):
    """Lets a test move time forward: clock.travel(hours=25)."""
    fake = helpers.FakeClock()
    monkeypatch.setattr(clock_module, "now", fake.now)
    return fake


@pytest.fixture
def admin_headers(client, db):
    return helpers.create_admin(client, db)
