"""Transactional emails via Resend. Internal only: no router.

Every function here is fire-and-forget: a failed email is logged and never fails the request.
Without a real RESEND_API_KEY (e.g. local dev with the .env.example placeholder) emails are
only logged.
"""

import logging
from datetime import date, time
from decimal import Decimal
from html import escape

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _resend_configured() -> bool:
    key = settings.RESEND_API_KEY
    return bool(key) and "xxxx" not in key


def send_email(to: str, subject: str, html: str) -> None:
    if not _resend_configured():
        logger.info("Email not sent (Resend not configured): to=%s subject=%r", to, subject)
        return
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({"from": settings.FROM_EMAIL, "to": [to], "subject": subject, "html": html})
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, to)


# ---------- Formatting helpers ----------

def _naira(amount: Decimal) -> str:
    return f"₦{amount:,.2f}"


def _date(d: date) -> str:
    return f"{DAY_NAMES[d.weekday()]} {d.day} {MONTH_NAMES[d.month - 1]} {d.year}"


def _time(t: time) -> str:
    return t.strftime("%H:%M")


def _wrap(name: str, body: str) -> str:
    return f"<p>Hi {escape(name)},</p>{body}<p>— The TutorLink team</p>"


# ---------- One function per email in CLAUDE.md ----------

def tutor_application_received(to: str, name: str) -> None:
    send_email(
        to,
        "We received your application",
        _wrap(name, "<p>Thanks for applying to tutor on TutorLink. We'll review your profile and get back to you soon.</p>"),
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


def schedule_booked(recipients: list[tuple[str, str]], subject: str, day_of_week: int,
                    start: time, end: time) -> None:
    day = DAY_NAMES[day_of_week]
    body = (
        f"<p>A weekly {escape(subject)} session has been booked for every {day}, "
        f"{_time(start)}–{_time(end)}.</p>"
    )
    for email, name in recipients:
        send_email(email, f"New session booked: {subject} every {day}", _wrap(name, body))


def schedule_cancelled(recipients: list[tuple[str, str]], subject: str, day_of_week: int,
                       start: time) -> None:
    day = DAY_NAMES[day_of_week]
    body = f"<p>The weekly {escape(subject)} session on {day}s at {_time(start)} has been cancelled.</p>"
    for email, name in recipients:
        send_email(email, "Session cancelled", _wrap(name, body))


def session_logged(to: str, name: str, subject: str, session_date: date,
                   topic_covered: str | None) -> None:
    topic = f"<p>Topic covered: {escape(topic_covered)}</p>" if topic_covered else ""
    send_email(
        to,
        f"Please confirm your {subject} session on {_date(session_date)}",
        _wrap(name, f"<p>Your tutor has logged a {escape(subject)} session on {_date(session_date)}.</p>"
                    f"{topic}<p>Please log in to confirm it.</p>"),
    )


def rate_tutor_prompt(to: str, name: str, tutor_name: str) -> None:
    """Not in the original CLAUDE.md email table: added with tutor ratings."""
    send_email(
        to,
        f"How was your lesson with {tutor_name}?",
        _wrap(name, f"<p>You've confirmed your first session with {escape(tutor_name)}. "
                    "Please take a moment to rate them. Your rating helps other parents choose the "
                    "best tutor.</p>"),
    )


def invoice_generated(to: str, name: str, month: int, year: int, total_sessions: int,
                      total_amount: Decimal) -> None:
    period = f"{MONTH_NAMES[month - 1]} {year}"
    send_email(
        to,
        f"Your TutorLink invoice for {period} is ready",
        _wrap(name, f"<p>Your invoice for {period} covers {total_sessions} confirmed session(s). "
                    f"Total due: {_naira(total_amount)}.</p>"),
    )


def payment_received(to: str, name: str, month: int, year: int, amount: Decimal) -> None:
    period = f"{MONTH_NAMES[month - 1]} {year}"
    send_email(
        to,
        "Payment received — thank you!",
        _wrap(name, f"<p>We received your payment of {_naira(amount)} for your {period} invoice.</p>"),
    )
