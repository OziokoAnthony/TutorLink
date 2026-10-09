"""Item 6 of the security review: one key per job, required in production."""

import pytest
from pydantic import ValidationError

from app.core import security, storage
from app.core.config import Settings, settings

STRONG = "k" * 40


def make(**overrides) -> Settings:
    values = {"SECRET_KEY": "s" * 40, "DATABASE_URL": "postgresql+psycopg://x@127.0.0.1/x", "APP_ENV": "production",
              "FILE_SIGNING_KEY": "f" * 40, "FIELD_ENCRYPTION_KEY": "e" * 40, "NIN_HASH_KEY": "n" * 40}
    return Settings(_env_file=None, **{**values, **overrides})


def test_production_needs_its_own_key_for_each_job():
    assert make()
    for name in ("FILE_SIGNING_KEY", "FIELD_ENCRYPTION_KEY", "NIN_HASH_KEY"):
        for bad in ("", "short", "your_key_here_" + "x" * 30, "s" * 40):  # unset, short, placeholder, = SECRET_KEY
            with pytest.raises(ValidationError):
                make(**{name: bad})


def test_development_derives_unset_keys_from_the_secret_key():
    assert make(APP_ENV="development", FILE_SIGNING_KEY="", FIELD_ENCRYPTION_KEY="", NIN_HASH_KEY="")


def test_each_key_changes_only_its_own_job(monkeypatch):
    before = (security.hash_nin("12345678901"), storage.local_signature("a/b.png", 1))
    pin = security.encrypt("1234")

    monkeypatch.setattr(settings, "NIN_HASH_KEY", STRONG)
    monkeypatch.setattr(settings, "FILE_SIGNING_KEY", STRONG)
    assert security.hash_nin("12345678901") != before[0]
    assert storage.local_signature("a/b.png", 1) != before[1]
    assert security.decrypt(pin) == "1234"  # FIELD_ENCRYPTION_KEY unchanged

    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", STRONG)
    with pytest.raises(Exception):
        security.decrypt(pin)
