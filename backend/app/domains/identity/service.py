"""ID documents before the NIN (spec 11 R1, R4) and the 90-day NIN deadline (R3)."""

from datetime import datetime
from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.core import clock, storage
from app.domains.auth.models import User
from app.domains.identity.models import (
    ID_LABELS,
    IdDocument,
    IdDocumentAdminView,
    IdDocumentStatus,
    IdDocumentTutorView,
    IdDocumentType,
    IdReviewIn,
)
from app.domains.notifications import service as notifications
from app.domains.notifications.service import date_text
from app.domains.tutors.models import NIN_DEADLINE, TutorProfile, VettingStatus

URL_SECONDS = 15 * 60
REMINDERS = (30, 7, 1, 0)  # days before the deadline; 0 is "it passed" (R3.5)


# ---------- The deadline (R3) ----------

def nin_due_at(profile: TutorProfile) -> datetime:
    return profile.created_at + NIN_DEADLINE


def nin_overdue(profile: TutorProfile, now: datetime | None = None) -> bool:
    return profile.nin_verified_at is None and (now or clock.now()) >= nin_due_at(profile)


def remind(session: Session, now: datetime) -> int:
    """Background job: the 30, 7 and 1 day reminders and the one when the deadline passes, each sent once."""
    profiles = session.exec(select(TutorProfile).where(
        TutorProfile.nin_verified_at.is_(None), TutorProfile.vetting_status != VettingStatus.rejected,
        (TutorProfile.nin_reminder_days.is_(None)) | (TutorProfile.nin_reminder_days > 0))).all()
    sent = 0
    for profile in profiles:
        left = nin_due_at(profile) - now
        reached = [d for d in REMINDERS if left.total_seconds() <= d * 86400]
        if not reached:
            continue
        days = min(reached)
        if profile.nin_reminder_days is not None and profile.nin_reminder_days <= days:
            continue
        due = date_text(nin_due_at(profile).astimezone(clock.WAT).date())
        if days == 0:
            title = "Parents can no longer see your profile"
            body = (f"You didn't verify your NIN by {due}, so parents can't find or book you. Lessons you already "
                    "have carry on. Verify your NIN on your dashboard and you'll be visible again at once.")
        else:
            title = f"Verify your NIN within {'1 day' if days == 1 else f'{days} days'}"
            body = (f"Please verify your NIN by {due}. After that, parents won't be able to find or book you "
                    "until you do.")
        notifications.notify(session, profile.user_id, title, body, "/dashboard/tutor")
        profile.nin_reminder_days = days
        session.add(profile)
        sent += 1
    session.commit()
    return sent


# ---------- Tutor (R1) ----------

def _profile(session: Session, user: User) -> TutorProfile:
    profile = session.exec(select(TutorProfile).where(TutorProfile.user_id == user.id)).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor profile not found")
    return profile


def _tutor_view(doc: IdDocument) -> IdDocumentTutorView:
    return IdDocumentTutorView.model_validate(doc, update={"file_url": storage.url(doc.file_key, URL_SECONDS)})


def has_uploaded(session: Session, tutor_id: UUID) -> bool:
    """A pending or verified ID: enough to upload certificates (R2.2)."""
    return session.exec(select(IdDocument.id).where(
        IdDocument.tutor_id == tutor_id, IdDocument.status != IdDocumentStatus.rejected)).first() is not None


def has_verified(session: Session, tutor_id: UUID) -> bool:
    return session.exec(select(IdDocument.id).where(
        IdDocument.tutor_id == tutor_id, IdDocument.status == IdDocumentStatus.verified)).first() is not None


def upload(session: Session, user: User, type_: IdDocumentType, file: UploadFile) -> IdDocumentTutorView:
    from app.domains.certificates.service import read_upload  # certificates asks has_uploaded

    _profile(session, user)
    if session.exec(select(IdDocument.id).where(IdDocument.tutor_id == user.id,
                                                IdDocument.status == IdDocumentStatus.pending)).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Your ID document is waiting for an admin to check it")
    data, extension, content_type = read_upload(file, "ID documents")
    key = f"id-documents/{user.id}/{uuid4().hex}.{extension}"
    storage.save(key, data, content_type)
    stem = PurePath((file.filename or "").replace("\\", "/")).stem.strip()[:100] or type_.value
    doc = IdDocument(tutor_id=user.id, type=type_, file_key=key, file_name=f"{stem}.{extension}")
    session.add(doc)
    try:
        session.commit()
    except Exception:
        storage.delete(key)
        raise
    session.refresh(doc)
    return _tutor_view(doc)


def list_mine(session: Session, user: User) -> list[IdDocumentTutorView]:
    rows = session.exec(select(IdDocument).where(IdDocument.tutor_id == user.id)
                        .order_by(IdDocument.created_at.desc())).all()
    return [_tutor_view(d) for d in rows]


# ---------- Admin (R1.2, R4.1) ----------

def _admin_views(session: Session, docs: list[IdDocument]) -> list[IdDocumentAdminView]:
    ids = {d.tutor_id for d in docs}
    profiles = {p.user_id: p for p in session.exec(
        select(TutorProfile).where(TutorProfile.user_id.in_(ids))).all()} if ids else {}
    return [IdDocumentAdminView(**_tutor_view(d).model_dump(), tutor_id=d.tutor_id,
                                tutor_first_name=profiles[d.tutor_id].first_name,
                                tutor_middle_name=profiles[d.tutor_id].middle_name,
                                tutor_surname=profiles[d.tutor_id].surname) for d in docs]


def admin_list(session: Session, status_filter: IdDocumentStatus | None,
               tutor_id: UUID | None) -> list[IdDocumentAdminView]:
    """Oldest first: `?status=pending` is the review queue."""
    stmt = select(IdDocument)
    if status_filter:
        stmt = stmt.where(IdDocument.status == status_filter)
    if tutor_id:
        stmt = stmt.where(IdDocument.tutor_id == tutor_id)
    return _admin_views(session, list(session.exec(stmt.order_by(IdDocument.created_at)).all()))


def review(session: Session, admin: User, doc_id: UUID, data: IdReviewIn) -> IdDocumentAdminView:
    doc = session.exec(select(IdDocument).where(IdDocument.id == doc_id).with_for_update()).first()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ID document not found")
    if doc.status != IdDocumentStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This ID document has already been reviewed")
    doc.status, doc.review_note = data.status, data.note
    doc.reviewed_by, doc.reviewed_at = admin.id, clock.now()
    session.add(doc)
    label = ID_LABELS[doc.type]
    if data.status == IdDocumentStatus.verified:
        notifications.notify(session, doc.tutor_id, f"Your {label} is verified",
                             f"An admin verified your {label}. Remember to verify your NIN within 90 days of "
                             "registering.", "/dashboard/tutor")
    else:
        notifications.notify(session, doc.tutor_id, f"Your {label} wasn't accepted",
                             f"An admin couldn't verify your {label}.\nReason: {data.note}\n"
                             "You can upload another ID document on your dashboard.", "/dashboard/tutor")
    session.commit()
    session.refresh(doc)
    return _admin_views(session, [doc])[0]
