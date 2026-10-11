"""Item 6 of the security review: one key per job, required in production; and production refuses to start
without the services it can't work without."""

import pytest
from pydantic import ValidationError

from app.core import security, storage
from app.core.config import Settings, settings

STRONG = "k" * 40

LIVE = {"PAYSTACK_SECRET_KEY": "sk_live_" + "p" * 40, "PAYSTACK_WEBHOOK_SECRET": "sk_live_" + "p" * 40,
        "PAYSTACK_DVA_BANK": "titan-paystack", "RESEND_API_KEY": "re_" + "r" * 30, "DOJAH_APP_ID": "app123",
        "DOJAH_SECRET_KEY": "prod_sk_" + "d" * 30, "DOJAH_BASE_URL": "https://api.dojah.io",
        "STORAGE_ENDPOINT_URL": "https://s3.us-west-004.backblazeb2.com", "STORAGE_ACCESS_KEY_ID": "key-id",
        "STORAGE_SECRET_ACCESS_KEY": "secret", "STORAGE_BUCKET": "tutorlink", "COOKIE_DOMAIN": "tutorlink.ng",
        "BASE_URL": "https://api.tutorlink.ng", "FRONTEND_URL": "https://tutorlink.ng"}


def make(**overrides) -> Settings:
    values = {"SECRET_KEY": "s" * 40, "DATABASE_URL": "postgresql+psycopg://x@127.0.0.1/x", "APP_ENV": "production",
              "FILE_SIGNING_KEY": "f" * 40, "FIELD_ENCRYPTION_KEY": "e" * 40, "NIN_HASH_KEY": "n" * 40, **LIVE}
    return Settings(_env_file=None, **{**values, **overrides})


def test_production_needs_its_own_key_for_each_job():
    assert make()
    for name in ("FILE_SIGNING_KEY", "FIELD_ENCRYPTION_KEY", "NIN_HASH_KEY"):
        for bad in ("", "short", "your_key_here_" + "x" * 30, "s" * 40):  # unset, short, placeholder, = SECRET_KEY
            with pytest.raises(ValidationError):
                make(**{name: bad})


@pytest.mark.parametrize("name, bad", [
    *[(name, "") for name in LIVE if name not in ("PAYSTACK_DVA_BANK", "DOJAH_BASE_URL")],
    ("RESEND_API_KEY", "re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"),  # the .env.example placeholder
    ("DOJAH_APP_ID", "your_dojah_app_id"),
    ("PAYSTACK_SECRET_KEY", "sk_test_" + "p" * 40),
    ("PAYSTACK_DVA_BANK", "test-bank"),
    ("DOJAH_BASE_URL", "https://sandbox.dojah.io"),
    ("BASE_URL", "http://api.tutorlink.ng"),
    ("FRONTEND_URL", "http://localhost:3000"),
])
def test_production_needs_live_services(name, bad):
    assert make()
    with pytest.raises(ValidationError, match=name):
        make(**{name: bad})


def test_development_runs_without_services():
    assert make(APP_ENV="development", **{name: "" for name in LIVE if name not in ("BASE_URL", "FRONTEND_URL")})


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
