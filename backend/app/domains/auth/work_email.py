"""Tutors' work emails: the initial of their surname, a dot and their first name at TUTOR_EMAIL_DOMAIN,
e.g. Anthony Ozioko -> o.anthony@tutorlink.com. The second Anthony Ozioko gets o.anthony2@tutorlink.com.
Stored lowercase, like every email; logging in with capitals (O.Anthony@tutorlink.com) works too."""

import unicodedata

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import settings
from app.domains.auth.models import User


def _letters(text: str) -> str:
    """ASCII letters only, lowercase: "Chí-Ọma" -> "chioma"."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in folded.lower() if "a" <= c <= "z")


def local_part(first_name: str, surname: str) -> str:
    """"Anthony", "Ozioko" -> "o.anthony". Only the first word of the first name is used."""
    first = _letters(first_name.split()[0]) if first_name.split() else ""
    initial = _letters(surname)[:1]
    return f"{initial or 't'}.{first or 'tutor'}"


def is_work_domain(email: str) -> bool:
    return email.lower().endswith("@" + settings.TUTOR_EMAIL_DOMAIN.lower())


def next_work_email(session: Session, first_name: str, surname: str) -> str:
    """The first free address: o.anthony@…, then o.anthony2@…, o.anthony3@…"""
    base, domain = local_part(first_name, surname), settings.TUTOR_EMAIL_DOMAIN.lower()
    taken = set(session.exec(
        select(func.lower(User.work_email)).where(func.lower(User.work_email).like(f"{base}%@{domain}"))
    ).all())
    n = 1
    while (candidate := f"{base}{n if n > 1 else ''}@{domain}") in taken:
        n += 1
    return candidate
