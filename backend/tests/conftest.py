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
from app.core import claude as claude_client
from app.core import dojah as dojah_client
from app.core import google as google_client
from app.core import paystack as paystack_client
from app.core import security
from app.core.config import settings
from app.domains.auth import service as auth_service
from app.domains.exam import service as exam_service
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
def google(monkeypatch):
    """Google ID tokens are checked against helpers.GOOGLE_KEY instead of Google's published keys, and the
    Google account photo is a generated image (no network). Set `google.photo = None` for no photo."""
    class FakeGoogle:
        photo: bytes | None = helpers.image_bytes()
        fetched: list[str] = []

        def fetch_photo(self, url):
            self.fetched.append(url)
            return self.photo if url else None

    fake = FakeGoogle()
    fake.fetched = []
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", helpers.GOOGLE_CLIENT_ID)
    monkeypatch.setattr(google_client, "signing_key", lambda token: helpers.GOOGLE_KEY.public_key())
    monkeypatch.setattr(google_client, "fetch_photo", fake.fetch_photo)
    return fake


@pytest.fixture(autouse=True)
def dojah(monkeypatch):
    """A fake Dojah: NIN lookups are answered by helpers.dojah, never over the network (spec 4 R3)."""
    fake = helpers.FakeDojah()
    monkeypatch.setattr(helpers, "dojah", fake)
    monkeypatch.setattr(dojah_client, "lookup_nin", fake.lookup_nin)
    return fake


@pytest.fixture(autouse=True)
def claude(monkeypatch, engine):
    """A fake Claude for the exam bank (spec 4 R5.2), answered by helpers.claude. Generation that would
    run in the background runs at once, on the test database."""
    fake = helpers.FakeClaude()
    monkeypatch.setattr(helpers, "claude", fake)
    monkeypatch.setattr(claude_client, "generate_questions", fake.generate_questions)
    monkeypatch.setattr(claude_client, "answer_question", fake.answer_question)
    monkeypatch.setattr(claude_client, "available", lambda: True)
    monkeypatch.setattr(exam_service, "run_in_background", lambda fn, *args: fn(*args))
    monkeypatch.setattr(exam_service, "new_session", lambda: Session(engine))
    return fake


@pytest.fixture(autouse=True)
def tutor_password(monkeypatch):
    """Tutors are emailed a generated password; tests get the known helpers.PASSWORD instead."""
    monkeypatch.setattr(auth_service, "generate_password", lambda: helpers.PASSWORD)
    return helpers.PASSWORD


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
