"""Rate limits on sign-in, sign-up and password reset, so passwords can't be guessed by the thousand and
sign-ups and reset emails can't be flooded.

Each rule counts attempts per key (an email or an IP address) in a sliding window; once a key reaches the
limit, further attempts get 429 until old ones fall out of the window. Attempts are rows in
`rate_limit_hits`, so limits hold across restarts and server processes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.core import clock
from app.core.config import settings
from app.domains.auth.models import RateLimitHit


@dataclass(frozen=True)
class Rule:
    name: str
    limit: int
    window: timedelta
    message: str


TRY_LATER = "Too many attempts. Please wait a few minutes and try again."

# Failed logins: per email, so one account can't be guessed at, and per IP, so one attacker can't guess
# across many accounts.
LOGIN_EMAIL = Rule("login-email", 10, timedelta(minutes=15),
                   "Too many wrong passwords for this email. Wait 15 minutes, or use \"Forgot password?\".")
LOGIN_IP = Rule("login-ip", 20, timedelta(minutes=15), TRY_LATER)
GOOGLE_IP = Rule("google-ip", 20, timedelta(minutes=15), TRY_LATER)
SIGNUP_IP = Rule("signup-ip", 10, timedelta(hours=1), "Too many sign-ups from here. Please try again later.")
RESET_EMAIL = Rule("reset-email", 3, timedelta(hours=1),
                   "We've already sent several reset links. Check your inbox and spam folder, or try again later.")
RESET_IP = Rule("reset-ip", 10, timedelta(hours=1), TRY_LATER)
RESET_USE_IP = Rule("reset-use-ip", 10, timedelta(minutes=15), TRY_LATER)


def client_ip(request: Request) -> str:
    """The caller's IP address. Behind a proxy or CDN (TRUST_PROXY_HEADERS), the first X-Forwarded-For
    address; otherwise the connection's, because anyone can send that header."""
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def _count(session: Session, key: str, since: datetime) -> int:
    return session.exec(select(func.count()).select_from(RateLimitHit)
                        .where(RateLimitHit.key == key, RateLimitHit.created_at > since)).one()


def check(session: Session, rule: Rule, subject: str, now: datetime | None = None) -> None:
    """429 (with Retry-After) when `subject` already has `rule.limit` attempts in the window."""
    if not settings.RATE_LIMITS_ENABLED:
        return
    now = now or clock.now()
    if _count(session, f"{rule.name}:{subject.lower()}", now - rule.window) >= rule.limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, rule.message,
                            headers={"Retry-After": str(int(rule.window.total_seconds()))})


def record(session: Session, rule: Rule, subject: str, now: datetime | None = None) -> None:
    """Counts one attempt. The caller commits, even when it then refuses the request."""
    if settings.RATE_LIMITS_ENABLED:
        session.add(RateLimitHit(key=f"{rule.name}:{subject.lower()}", created_at=now or clock.now()))


def hit(session: Session, rule: Rule, subject: str) -> None:
    """Checks and counts in one go, for attempts that count whether or not they succeed."""
    check(session, rule, subject)
    record(session, rule, subject)
    session.commit()


def delete_old(session: Session, now: datetime) -> int:
    """Background job: forget attempts older than the longest window."""
    result = session.exec(delete(RateLimitHit).where(RateLimitHit.created_at < now - timedelta(days=1)))
    session.commit()
    return result.rowcount
