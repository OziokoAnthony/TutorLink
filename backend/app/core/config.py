from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_placeholder(value: str) -> bool:
    """True for an empty secret or one still copied from .env.example (which is public on GitHub)."""
    return not value or "xxxx" in value or value.startswith("your_")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
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
    # Tutors are assigned a work email at this domain (e.g. o.anthony@tutorlink.com) and log in with it.
    TUTOR_EMAIL_DOMAIN: str = "tutorlink.com"

    # Google sign-in (spec 4 R1): the OAuth Client ID that Google ID tokens must be issued for.
    GOOGLE_CLIENT_ID: str = ""

    # Dojah NIN verification (spec 4 R3). Sandbox until going live: https://api.dojah.io
    DOJAH_APP_ID: str = ""
    DOJAH_SECRET_KEY: str = ""
    DOJAH_BASE_URL: str = "https://sandbox.dojah.io"

    # Claude writes and checks the qualifying exam's questions (spec 4 R5.2).
    ANTHROPIC_API_KEY: str = ""
    EXAM_MODEL: str = "claude-opus-5-5"

    # A private S3-compatible bucket for uploaded files (Backblaze B2, Cloudflare R2…). While unset, files are
    # kept under LOCAL_STORAGE_DIR (development only).
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_REGION: str = "auto"
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_BUCKET: str = ""
    LOCAL_STORAGE_DIR: str = "storage"

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


settings = Settings()
