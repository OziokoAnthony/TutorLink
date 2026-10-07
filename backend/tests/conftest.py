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

from app.core import security
from app.core.config import settings
from app.db.session import get_session
from app.domains.billing import service as billing_service
from app.domains.notifications import service as notifications
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
def paystack_secrets(monkeypatch):
    """Real-looking Paystack secrets, whatever the developer's .env holds."""
    monkeypatch.setattr(settings, "PAYSTACK_SECRET_KEY", "sk_test_tutorlink_tests")
    monkeypatch.setattr(settings, "PAYSTACK_WEBHOOK_SECRET", "sk_test_tutorlink_tests")


@pytest.fixture
def paystack_transactions(monkeypatch):
    """Fakes Paystack's Verify Transaction API: reference -> transaction `data` as Paystack reports it."""
    transactions: dict[str, dict] = {}
    monkeypatch.setattr(billing_service, "verify_paystack_transaction",
                        lambda reference: transactions.get(reference, {}))
    return transactions


@pytest.fixture
def paystack(monkeypatch, paystack_transactions):
    """Fakes Paystack's Initialize Transaction API and records the calls.
    Every started transaction counts as successfully paid unless a test edits `paystack_transactions`."""
    calls: list[dict] = []

    def fake_initialize(**kwargs):
        calls.append(kwargs)
        paystack_transactions[kwargs["reference"]] = {
            "status": "success", "reference": kwargs["reference"],
            "amount": kwargs["amount_kobo"], "currency": "NGN",
        }
        return {
            "authorization_url": f"https://checkout.paystack.com/{kwargs['reference']}",
            "access_code": "test_access_code",
            "reference": kwargs["reference"],
        }

    monkeypatch.setattr(billing_service, "initialize_paystack_transaction", fake_initialize)
    return calls


@pytest.fixture
def admin_headers(client, db):
    return helpers.create_admin(client, db)
