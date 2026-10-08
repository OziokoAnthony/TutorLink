from datetime import datetime, timedelta, timezone
from typing import Any

import base64
import hashlib
import hmac
import secrets

import jwt
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# No 0/O or 1/l/I, so a password read from an email is typed correctly.
_PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_password(length: int = 12) -> str:
    """A random password for a tutor, emailed to them at registration (spec 4 R0.3)."""
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    """False when the user has no password (a parent who signed up with Google)."""
    return password_hash is not None and pwd_context.verify(plain_password, password_hash)


def hash_token(token: str) -> str:
    """SHA-256 of a random one-time token, e.g. a password reset link's. Only the hash is stored."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_nin(nin: str) -> str:
    """A one-way, keyed hash of a NIN, so one NIN verifies one account (spec 4 R3.6) without storing it.
    Keyed because there are only 10^11 NINs: a plain hash could be reversed by trying them all.
    Changing SECRET_KEY changes every hash, so already-verified NINs could then verify again."""
    key = hmac.new(settings.SECRET_KEY.encode(), b"tutorlink-nin", hashlib.sha256).digest()
    return hmac.new(key, nin.encode(), hashlib.sha256).hexdigest()


def _fernet() -> Fernet:
    key = hmac.new(settings.SECRET_KEY.encode(), b"tutorlink-secret-fields", hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    """Encrypts a short secret kept only until it's used, e.g. a WAEC/NECO checker PIN (spec 4 R4.2).
    The key comes from SECRET_KEY: changing it makes stored values unreadable."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
