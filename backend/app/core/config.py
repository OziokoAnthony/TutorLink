from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_placeholder(value: str) -> bool:
    """True for an empty secret or one still copied from .env.example (which is public on GitHub)."""
    return not value or "xxxx" in value or value.startswith("your_")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str  # signs login tokens
    # One key per job, so a leak of one doesn't give away the others. Unset, each is derived from SECRET_KEY
    # (fine while developing); production requires all three, different from SECRET_KEY. Changing one later
    # has a cost: FILE_SIGNING_KEY breaks file links already handed out, FIELD_ENCRYPTION_KEY makes stored
    # checker PINs unreadable, and NIN_HASH_KEY lets already-verified NINs verify a second account.
    FILE_SIGNING_KEY: str = ""
    FIELD_ENCRYPTION_KEY: str = ""
    NIN_HASH_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ADMIN_TOKEN_EXPIRE_MINUTES: int = 240
    # The login cookie's domain. Unset on localhost; in production the parent domain shared by the site and the
    # API (e.g. "tutorlink.ng" for www.tutorlink.ng and api.tutorlink.ng), so the site's middleware can read it.
    COOKIE_DOMAIN: str | None = None
    BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    DATABASE_URL: str
    ALEMBIC_DATABASE_URL: str | None = None

    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""
    # Bank for parents' dedicated account numbers: "test-bank" in Paystack test mode, e.g. "titan-paystack" live.
    PAYSTACK_DVA_BANK: str = "test-bank"

    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@tutorlink.ng"

    # Google sign-in (spec 4 R1): the OAuth Client ID that Google ID tokens must be issued for.
    GOOGLE_CLIENT_ID: str = ""

    # Dojah NIN verification (spec 4 R3). Sandbox until going live: https://api.dojah.io
    DOJAH_APP_ID: str = ""
    DOJAH_SECRET_KEY: str = ""
    DOJAH_BASE_URL: str = "https://sandbox.dojah.io"

    # Claude writes and checks the qualifying exam's questions (spec 4 R5.2).
    ANTHROPIC_API_KEY: str = ""
    EXAM_MODEL: str = "claude-opus-5-5"
    HELP_MODEL: str = "claude-opus-5-5"  # the help assistant (spec 6 R3)

    # A private S3-compatible bucket for uploaded files (Backblaze B2, Cloudflare R2…). While unset, files are
    # kept under LOCAL_STORAGE_DIR (development only).
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_REGION: str = "auto"
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_BUCKET: str = ""
    LOCAL_STORAGE_DIR: str = "storage"

    # Limits on login, sign-up and password-reset attempts (app/domains/auth/limits.py).
    RATE_LIMITS_ENABLED: bool = True
    # True only behind a proxy or CDN that sets X-Forwarded-For (Render, Cloudflare…); otherwise anyone could
    # fake their IP address with that header.
    TRUST_PROXY_HEADERS: bool = False

    # Background jobs (expiries, due payments, payable earnings) run inside the API process.
    RUN_SCHEDULER: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 60

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_is_real(cls, v: str) -> str:
        # Anyone who knows the key can sign an admin token, so the public example value is refused.
        if is_placeholder(v):
            raise ValueError("SECRET_KEY is still the .env.example placeholder; generate one with "
                             "python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def production_keys_are_separate(self) -> "Settings":
        if self.APP_ENV != "production":
            return self
        for name in ("FILE_SIGNING_KEY", "FIELD_ENCRYPTION_KEY", "NIN_HASH_KEY"):
            value = getattr(self, name)
            if is_placeholder(value) or len(value) < 32 or value == self.SECRET_KEY:
                raise ValueError(f"In production, {name} must be its own random key of 32+ characters, "
                                 "different from SECRET_KEY")
        return self

    @model_validator(mode="after")
    def production_services_are_live(self) -> "Settings":
        """Without these, production would start and then fail quietly: files saved to the container's disk and
        lost on redeploy, no emails (so no password resets), no payments, and no NIN checks (so no tutor can be
        approved). Google sign-in and Claude stay optional: their features say they're off."""
        if self.APP_ENV != "production":
            return self
        missing = [name for name in ("PAYSTACK_SECRET_KEY", "PAYSTACK_WEBHOOK_SECRET", "RESEND_API_KEY",
                                     "DOJAH_APP_ID", "DOJAH_SECRET_KEY", "STORAGE_ENDPOINT_URL",
                                     "STORAGE_ACCESS_KEY_ID", "STORAGE_SECRET_ACCESS_KEY", "STORAGE_BUCKET",
                                     "COOKIE_DOMAIN")
                   if is_placeholder(getattr(self, name) or "")]
        if self.PAYSTACK_SECRET_KEY.startswith("sk_test_"):
            missing.append("PAYSTACK_SECRET_KEY (a live sk_live_ key, not a test key)")
        if self.PAYSTACK_DVA_BANK == "test-bank":
            missing.append("PAYSTACK_DVA_BANK (a live bank such as titan-paystack, not test-bank)")
        if "sandbox" in self.DOJAH_BASE_URL:
            missing.append("DOJAH_BASE_URL (https://api.dojah.io, not the sandbox)")
        for name in ("BASE_URL", "FRONTEND_URL"):
            if not getattr(self, name).startswith("https://"):
                missing.append(f"{name} (an https:// address)")
        if missing:
            raise ValueError("In production, set: " + "; ".join(missing))
        return self


settings = Settings()
