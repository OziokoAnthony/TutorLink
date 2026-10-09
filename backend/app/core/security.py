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
def verify_password(plain_password: str, password_hash: str | None) -> bool:
    """False when the user has no password (a parent who signed up with Google)."""
    return password_hash is not None and pwd_context.verify(plain_password, password_hash)


def hash_token(token: str) -> str:
    """SHA-256 of a random one-time token, e.g. a password reset link's. Only the hash is stored."""
    return hashlib.sha256(token.encode()).hexdigest()


def _key_for(dedicated: str, purpose: bytes) -> bytes:
    """A key for one job: from its own setting, or (unset, while developing) derived from SECRET_KEY as
    before the keys were split, so existing hashes and encrypted values stay valid."""
    return hmac.new((dedicated or settings.SECRET_KEY).encode(), purpose, hashlib.sha256).digest()


def hash_nin(nin: str) -> str:
    """A one-way, keyed hash of a NIN, so one NIN verifies one account (spec 4 R3.6) without storing it.
    Keyed because there are only 10^11 NINs: a plain hash could be reversed by trying them all.
    Changing NIN_HASH_KEY changes every hash, so already-verified NINs could then verify again."""
    key = _key_for(settings.NIN_HASH_KEY, b"tutorlink-nin")
    return hmac.new(key, nin.encode(), hashlib.sha256).hexdigest()


def _fernet() -> Fernet:
    key = _key_for(settings.FIELD_ENCRYPTION_KEY, b"tutorlink-secret-fields")
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value: str) -> str:
    """Encrypts a short secret kept only until it's used, e.g. a WAEC/NECO checker PIN (spec 4 R4.2).
    The key comes from FIELD_ENCRYPTION_KEY: changing it makes stored values unreadable."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def token_lifetime(role: str) -> timedelta:
    """Admins' sessions are shorter: an admin token can approve tutors and send money."""
    minutes = settings.ADMIN_TOKEN_EXPIRE_MINUTES if role == "admin" else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return timedelta(minutes=minutes)


def create_access_token(subject: str, role: str, version: int = 0, expires_delta: timedelta | None = None) -> str:
    """`version` is the user's token_version: raising it (on a password change or reset) ends every session."""
    expire = datetime.now(timezone.utc) + (expires_delta or token_lifetime(role))
    payload = {"sub": str(subject), "role": role, "ver": version, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError if the token is invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
