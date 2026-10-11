"""Notifications: an in-app list per user, plus emails via Resend.

`notify()` adds the in-app notification to the caller's database session and queues the email; the
email is only sent once that session commits, so a rolled-back change never emails anyone.
Emails are fire-and-forget: a failed email is logged and never fails the request. Without a real
RESEND_API_KEY (e.g. local dev with the .env.example placeholder) emails are only logged.
"""

import logging
from datetime import date, time
from decimal import Decimal
from html import escape
from uuid import UUID

import resend
from sqlalchemy import event, func
from sqlalchemy.orm import Session as OrmSession
from sqlmodel import Session, select

from app.core.config import is_placeholder, settings
from app.db.base import utcnow
from app.domains.notifications.models import Notification, NotificationList, NotificationRead

logger = logging.getLogger(__name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _resend_configured() -> bool:
    return not is_placeholder(settings.RESEND_API_KEY)


def send_email(to: str, subject: str, html: str) -> None:
    if not _resend_configured():
        logger.info("Email not sent (Resend not configured): to=%s subject=%r", to, subject)
        return
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({"from": settings.FROM_EMAIL, "to": [to], "subject": subject, "html": html})
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, to)


def _wrap(name: str, body: str) -> str:
    return f"<p>Hi {escape(name)},</p>{body}<p>— The TutorLink team</p>"


# ---------- In-app notifications + email ----------

_OUTBOX = "notification_emails"


def notify(session: Session, user_id: UUID, title: str, body: str, link: str | None = None,
           *, email: bool = True) -> None:
    """Records an in-app notification and, after the caller commits, emails the same message."""
    session.add(Notification(user_id=user_id, title=title, body=body, link=link))
    if email:
        from app.domains.auth.models import User  # auth imports this module

        user = session.get(User, user_id)
        if user is not None:
            html = "".join(f"<p>{escape(line)}</p>" for line in body.splitlines() if line.strip())
            if link:
                html += f'<p><a href="{escape(settings.FRONTEND_URL + link)}">Open TutorLink</a></p>'
            session.info.setdefault(_OUTBOX, []).append((user.email, title, html + "<p>— The TutorLink team</p>"))


@event.listens_for(OrmSession, "after_commit")
def _send_queued_emails(orm_session) -> None:
    for to, subject, html in orm_session.info.pop(_OUTBOX, []):
        send_email(to, subject, html)


@event.listens_for(OrmSession, "after_rollback")
def _drop_queued_emails(orm_session) -> None:
    orm_session.info.pop(_OUTBOX, None)


def list_mine(session: Session, user_id: UUID, limit: int) -> NotificationList:
    items = session.exec(
        select(Notification).where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    unread = session.exec(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ).one()
    return NotificationList(unread_count=unread, items=[NotificationRead.model_validate(n) for n in items])


def mark_read(session: Session, user_id: UUID, notification_id: UUID | None) -> None:
    """Marks one notification (or, with None, all of the user's) as read."""
    stmt = select(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
    if notification_id is not None:
        stmt = stmt.where(Notification.id == notification_id)
    for notification in session.exec(stmt).all():
        notification.read_at = utcnow()
        session.add(notification)
    session.commit()


# ---------- Account emails (email only) ----------

def tutor_application_received(to: str, name: str) -> None:
    """Tells a new tutor their application is in and what to do next."""
    send_email(
        to,
        "We received your application",
        _wrap(name, "<p>Thanks for applying to tutor on TutorLink. We'll review your profile and get back to you soon.</p>"
                    "<p>Log in with this email address to finish the steps on your dashboard: your picture, NIN, "
                    "a certificate and the qualifying exam.</p>"),
    )


def password_reset_email(name: str, link: str) -> tuple[str, str]:
    """(subject, html) of the "Forgot password?" email (spec 4 R0.7)."""
    return "Reset your TutorLink password", _wrap(
        name,
        "<p>To set a new password, open this link. It works once and expires in 1 hour.</p>"
        f'<p><a href="{escape(link)}">Set a new password</a></p>'
        "<p>If you didn't ask for this, you can ignore this email: your password stays the same.</p>",
    )


def tutor_approved(to: str, name: str) -> None:
    send_email(
        to,
        "You're approved! Welcome to TutorLink",
        _wrap(name, "<p>Your tutor profile has been approved. Parents can now find and book you.</p>"),
    )


def tutor_rejected(to: str, name: str, note: str | None) -> None:
    reason = f"<p>Reviewer's note: {escape(note)}</p>" if note else ""
    send_email(
        to,
        "Update on your TutorLink application",
        _wrap(name, f"<p>Unfortunately we can't approve your tutor application right now.</p>{reason}"),
    )


# ---------- Formatting for notification text ----------

def naira(amount: Decimal) -> str:
    return f"₦{amount:,.2f}"


def date_text(d: date) -> str:
    return f"{DAY_NAMES[d.weekday()]} {d.day} {MONTH_NAMES[d.month - 1]} {d.year}"


def time_text(t: time) -> str:
    return t.strftime("%H:%M")
