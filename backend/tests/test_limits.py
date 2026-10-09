"""Rate limits on login, sign-up and password reset (app/domains/auth/limits.py)."""

from datetime import timedelta

import pytest

from app.core.config import settings
from tests import helpers
from tests.helpers import PASSWORD


@pytest.fixture(autouse=True)
def limits_on(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMITS_ENABLED", True)


def login(client, email, password):
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def test_ten_wrong_passwords_lock_the_email_for_15_minutes(client, clock):
    helpers.register_parent(client, email="ada@example.com", photo=False)
    for _ in range(10):
        assert login(client, "ada@example.com", "wrong-password").status_code == 401
    locked = login(client, "ada@example.com", PASSWORD)  # even the right password
    assert locked.status_code == 429 and "Forgot password" in locked.json()["detail"]
    assert locked.headers["Retry-After"]

    clock.travel(minutes=16)
    assert login(client, "ada@example.com", PASSWORD).status_code == 200


def test_successful_logins_are_not_counted(client):
    helpers.register_parent(client, email="ada@example.com", photo=False)
    for _ in range(15):
        assert login(client, "ada@example.com", PASSWORD).status_code == 200


def test_one_address_guessing_across_many_emails_is_stopped(client):
    for i in range(20):
        assert login(client, f"nobody{i}@example.com", "guess").status_code == 401
    assert login(client, "someone-else@example.com", "guess").status_code == 429


def test_sign_ups_are_limited_per_address(client):
    for i in range(10):
        helpers.register_parent(client, email=f"parent{i}@example.com", photo=False)
    body = {"email": "one-more@example.com", "password": PASSWORD, "role": "parent", "full_name": "Ada Parent"}
    assert client.post("/v1/auth/register", json=body).status_code == 429


def test_reset_emails_are_limited_per_email_whether_or_not_it_exists(client, outbox):
    helpers.register_parent(client, email="ada@example.com", photo=False)
    for email in ("ada@example.com", "nobody@example.com"):
        for _ in range(3):
            assert client.post("/v1/auth/forgot-password", json={"email": email}).status_code == 202
        assert client.post("/v1/auth/forgot-password", json={"email": email}).status_code == 429
    assert [e["to"] for e in outbox].count("ada@example.com") == 3


def test_old_attempts_are_deleted_by_the_background_jobs(client, db, clock):
    from sqlmodel import func, select

    from app.domains.auth.models import RateLimitHit
    login(client, "nobody@example.com", "guess")
    assert db.exec(select(func.count()).select_from(RateLimitHit)).one() == 2  # per email and per IP
    clock.travel(days=1, minutes=1)
    helpers.run_jobs(db, clock)
    assert db.exec(select(func.count()).select_from(RateLimitHit)).one() == 0
