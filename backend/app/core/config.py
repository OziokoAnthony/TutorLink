from decimal import Decimal

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
    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""

    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@tutorlink.ng"

    COMMISSION_RATE: Decimal = Decimal("0.10")

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
