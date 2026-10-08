"""Tutor onboarding checklist (spec 4 R2) and NIN verification with Dojah (R3)."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core import clock, dojah
from app.core.security import hash_nin
from app.domains.auth import photos
from app.domains.auth.models import User
from app.domains.certificates import service as certificates
from app.domains.certificates.models import CertificateStatus
from app.domains.onboarding.models import (
    NinCheckRead,
    NinResult,
    NinVerification,
    Onboarding,
    OnboardingStep,
)
from app.domains.tutors.models import TutorOffer, TutorProfile, VettingStatus

NIN_ATTEMPTS = 3  # per 24 hours, because each lookup costs money (R3.8)
NIN_WINDOW = timedelta(hours=24)

NAME_MISMATCH = "Your name doesn't match your NIN record"


def _profile(session: Session, user: User, *, lock: bool = False) -> TutorProfile:
    stmt = select(TutorProfile).where(TutorProfile.user_id == user.id)
    if lock:
        stmt = stmt.with_for_update()
    profile = session.exec(stmt).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor profile not found")
    return profile


# ---------- Checklist (R2) ----------

def profile_todo(session: Session, user: User) -> list[str]:
    """What the Profile step still needs: a picture (R1b.2) and at least one offer (R2.1)."""
    todo = []
    if user.photo_key is None:
        todo.append("Add a profile picture")
    has_offer = session.exec(
        select(func.count()).select_from(TutorOffer)
        .where(TutorOffer.tutor_id == user.id, TutorOffer.is_active == True)  # noqa: E712
    ).one()
    if not has_offer:
        todo.append("Add at least one offer")
    return todo


def _recent_attempts(session: Session, tutor_id: UUID, now: datetime) -> list[datetime]:
    return list(session.exec(
        select(NinVerification.checked_at)
        .where(NinVerification.tutor_id == tutor_id, NinVerification.checked_at > now - NIN_WINDOW)
        .order_by(NinVerification.checked_at)
    ).all())


def _retry_at(attempts: list[datetime]) -> datetime | None:
    """When the oldest attempt in the window drops out, if every attempt is used."""
    return attempts[-NIN_ATTEMPTS] + NIN_WINDOW if len(attempts) >= NIN_ATTEMPTS else None


def certificates_todo(session: Session, user: User) -> list[str]:
    """What the Certificates step still needs: one certificate an admin verified (R2.3, R4.3)."""
    statuses = certificates.statuses_of(session, user.id)
    if CertificateStatus.verified in statuses:
        return []
    if CertificateStatus.pending in statuses:
        return ["Wait for an admin to check your certificate"]
    if CertificateStatus.rejected in statuses:
        return ["Upload a replacement for your rejected certificate"]
    return ["Upload at least one certificate"]


def get_onboarding(session: Session, user: User) -> Onboarding:
    profile = _profile(session, user)
    attempts = _recent_attempts(session, user.id, clock.now())
    todo = profile_todo(session, user)
    certs = certificates_todo(session, user)
    nin_done = profile.nin_verified_at is not None
    return Onboarding(
        steps=[
            OnboardingStep(key="profile", done=not todo, todo=todo),
            OnboardingStep(key="nin", done=nin_done, todo=[] if nin_done else ["Verify your NIN with a selfie"]),
            OnboardingStep(key="certificates", done=not certs, todo=certs),
            OnboardingStep(key="review", done=profile.vetting_status == VettingStatus.approved,
                           todo=missing_for_approval(session, profile)),
        ],
        vetting_status=profile.vetting_status.value,
        nin_attempts_left=0 if nin_done else max(0, NIN_ATTEMPTS - len(attempts)),
        nin_retry_at=None if nin_done else _retry_at(attempts),
    )


def missing_for_approval(session: Session, profile: TutorProfile) -> list[str]:
    """What stops an admin approving this tutor (R2.3). The quiz (R5) joins when built."""
    missing = []
    if profile.nin_verified_at is None:
        missing.append("NIN not verified")
    if not certificates.has_verified(session, profile.user_id):
        missing.append("no verified certificate")
    return missing


# ---------- NIN verification (R3) ----------

def _same_name(ours: str | None, theirs: str | None) -> bool:
    """Equal ignoring only capital letters and extra spaces (R3.3): any other difference is a mismatch."""
    def norm(name: str | None) -> str:
        return " ".join((name or "").split()).casefold()
    return norm(ours) == norm(theirs)


def _message(row: NinVerification) -> str:
    if row.verified:
        return "Your NIN is verified"
    if not row.nin_found:
        return "We couldn't find this NIN. Check the 11 digits and try again."
    if not row.name_matches:
        # The NIN record's name is never shown, so a stranger's NIN reveals nothing (R3.4).
        return f"{NAME_MISMATCH}. Correct your name to match it exactly, then try again."
    return "Your selfie doesn't match your NIN photo. Take a clear selfie in good light and try again."


def verify_nin(session: Session, user: User, nin: str, selfie: bytes) -> NinResult:
    """Checks the NIN exists, the tutor's name matches it exactly and the selfie matches its photo
    (R3.3). Verified only when all three pass; there's no override (R3.4)."""
    profile = _profile(session, user, lock=True)  # one attempt at a time, so the limit holds
    if profile.nin_verified_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Your NIN is already verified")
    if todo := profile_todo(session, user):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Complete your profile first: {todo[0].lower()}")

    now = clock.now()
    attempts = _recent_attempts(session, user.id, now)
    if retry_at := _retry_at(attempts):
        at = retry_at.astimezone(clock.WAT).strftime("%H:%M on %d %b")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"You've used all {NIN_ATTEMPTS} NIN checks for 24 hours. Try again after {at} (WAT).")

    nin_hash = hash_nin(nin)
    taken = session.exec(select(NinVerification.id).where(
        NinVerification.nin_hash == nin_hash, NinVerification.verified == True,  # noqa: E712
        NinVerification.tutor_id != user.id,
    )).first()
    if taken:  # checked before calling Dojah, so it costs nothing (R3.6)
        raise HTTPException(status.HTTP_409_CONFLICT, "This NIN is already verified on another TutorLink account")

    record = dojah.lookup_nin(nin, photos.square_jpeg(selfie, "Selfies"))
    row = NinVerification(tutor_id=user.id, nin_last4=nin[-4:], nin_hash=nin_hash, nin_found=record is not None,
                          verified=False, checked_at=now)
    if record is not None:
        row.name_matches = (_same_name(profile.first_name, record.first_name)
                            and _same_name(profile.middle_name, record.middle_name)
                            and _same_name(profile.surname, record.surname))
        row.selfie_matches = record.selfie_matches
        row.verified = row.name_matches and row.selfie_matches
        row.dojah_reference = record.reference
    session.add(row)
    if row.verified:
        profile.nin_verified_at = now  # locks the name (R3.5)
        session.add(profile)
    try:
        session.commit()
    except IntegrityError:  # the same NIN verified on another account at this very moment
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This NIN is already verified on another TutorLink account")
    session.refresh(row)
    return NinResult(**NinCheckRead.model_validate(row).model_dump(), message=_message(row),
                     attempts_left=0 if row.verified else NIN_ATTEMPTS - len(attempts) - 1)


def latest_checks(session: Session, tutor_ids: list[UUID]) -> dict[UUID, NinCheckRead]:
    """tutor id -> their latest NIN check (R3.9), one query for any number of tutors."""
    if not tutor_ids:
        return {}
    rows = session.exec(
        select(NinVerification).where(NinVerification.tutor_id.in_(tutor_ids))
        .distinct(NinVerification.tutor_id)
        .order_by(NinVerification.tutor_id, NinVerification.checked_at.desc())
    ).all()
    return {row.tutor_id: NinCheckRead.model_validate(row) for row in rows}
