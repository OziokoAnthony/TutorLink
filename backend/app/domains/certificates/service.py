"""Certificates (spec 4 R4): the tutor uploads them after verifying their NIN, an admin checks each one."""

from collections import defaultdict
from pathlib import PurePath
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.core import storage
from app.core.security import decrypt, encrypt
from app.db.base import utcnow
from app.domains.auth.models import User
from app.domains.certificates.models import (
    Certificate,
    CertificateAdminView,
    CertificateFields,
    CertificateStatus,
    CertificateTutorView,
    CertificateType,
    ReviewRequest,
)
from app.domains.notifications import service as notifications
from app.domains.tutors.models import TutorProfile

MAX_BYTES = 10 * 1024 * 1024
URL_SECONDS = 15 * 60
# Recognised by their first bytes, not by the name or type the browser claims (R4.1).
FORMATS = ((b"%PDF-", "pdf", "application/pdf"), (b"\xff\xd8\xff", "jpg", "image/jpeg"),
           (b"\x89PNG\r\n\x1a\n", "png", "image/png"))



def read_upload(file: UploadFile) -> tuple[bytes, str, str]:
    """(data, extension, content type) of a PDF, JPG or PNG up to 10 MB."""
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Certificates can be at most 10 MB")
    for magic, extension, content_type in FORMATS:
        if data.startswith(magic):
            return data, extension, content_type
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Certificates must be a PDF, JPG or PNG file")


def _file_name(name: str | None, extension: str) -> str:
    stem = PurePath((name or "").replace("\\", "/")).stem.strip()[:100] or "certificate"
    return f"{stem}.{extension}"


def _tutor_view(c: Certificate) -> CertificateTutorView:
    return CertificateTutorView.model_validate(c, update={
        "file_url": storage.url(c.file_key, URL_SECONDS), "has_checker_pin": c.checker_pin_encrypted is not None})


def _admin_views(session: Session, certificates: list[Certificate]) -> list[CertificateAdminView]:
    tutor_ids = {c.tutor_id for c in certificates}
    profiles = {p.user_id: p for p in session.exec(
        select(TutorProfile).where(TutorProfile.user_id.in_(tutor_ids))).all()} if tutor_ids else {}
    views = []
    for c in certificates:
        profile = profiles[c.tutor_id]
        views.append(CertificateAdminView(
            **_tutor_view(c).model_dump(), tutor_id=c.tutor_id,
            tutor_first_name=profile.first_name, tutor_middle_name=profile.middle_name,
            tutor_surname=profile.surname, tutor_nin_verified=profile.nin_verified_at is not None,
            checker_pin=decrypt(c.checker_pin_encrypted) if c.checker_pin_encrypted else None,
        ))
    return views


# ---------- Tutor ----------

def upload(session: Session, user: User, fields: CertificateFields, file: UploadFile) -> CertificateTutorView:
    profile = session.exec(select(TutorProfile).where(TutorProfile.user_id == user.id)).first()
    if profile is None or profile.nin_verified_at is None:
        # Certificates are checked against the NIN-verified name, so that comes first (R3.4, R4.3).
        raise HTTPException(status.HTTP_409_CONFLICT, "Verify your NIN before uploading certificates")
    data, extension, content_type = read_upload(file)
    key = f"certificates/{user.id}/{uuid4().hex}.{extension}"
    storage.save(key, data, content_type)
    certificate = Certificate(
        tutor_id=user.id, type=fields.type, institution=fields.institution, year=fields.year,
        file_key=key, file_name=_file_name(file.filename, extension),
        exam_number=fields.exam_number, exam_year=fields.exam_year,
        checker_pin_encrypted=encrypt(fields.checker_pin) if fields.checker_pin else None,
    )
    session.add(certificate)
    try:
        session.commit()
    except Exception:
        storage.delete(key)
        raise
    session.refresh(certificate)
    return _tutor_view(certificate)


def list_mine(session: Session, user: User) -> list[CertificateTutorView]:
    rows = session.exec(select(Certificate).where(Certificate.tutor_id == user.id)
                        .order_by(Certificate.created_at.desc())).all()
    return [_tutor_view(c) for c in rows]


# ---------- Admin (R4.3) ----------

def admin_list(session: Session, status_filter: CertificateStatus | None,
               tutor_id: UUID | None) -> list[CertificateAdminView]:
    stmt = select(Certificate)
    if status_filter:
        stmt = stmt.where(Certificate.status == status_filter)
    if tutor_id:
        stmt = stmt.where(Certificate.tutor_id == tutor_id)
    return _admin_views(session, list(session.exec(stmt.order_by(Certificate.created_at)).all()))


def review(session: Session, admin: User, certificate_id: UUID, data: ReviewRequest) -> CertificateAdminView:
    certificate = session.exec(select(Certificate).where(Certificate.id == certificate_id).with_for_update()).first()
    if certificate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Certificate not found")
    if certificate.status != CertificateStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This certificate has already been reviewed")
    certificate.status = data.status
    certificate.review_note = data.note
    certificate.reviewed_by = admin.id
    certificate.reviewed_at = utcnow()
    certificate.checker_pin_encrypted = None  # used up: erased once reviewed (R4.2)
    session.add(certificate)

    label = certificate.type.value
    if data.status == CertificateStatus.verified:
        notifications.notify(session, certificate.tutor_id, f"Your {label} certificate is verified",
                             f"An admin verified your {label} certificate from {certificate.institution}.",
                             "/dashboard/tutor")
    else:
        notifications.notify(session, certificate.tutor_id, f"Your {label} certificate wasn't accepted",
                             f"An admin couldn't verify your {label} certificate from {certificate.institution}.\n"
                             f"Reason: {data.note}\nYou can upload a replacement on your dashboard.",
                             "/dashboard/tutor")
    session.commit()
    session.refresh(certificate)
    return _admin_views(session, [certificate])[0]


# ---------- Used by onboarding and the tutor listing ----------

def has_verified(session: Session, tutor_id: UUID) -> bool:
    return session.exec(select(Certificate.id).where(
        Certificate.tutor_id == tutor_id, Certificate.status == CertificateStatus.verified)).first() is not None


def statuses_of(session: Session, tutor_id: UUID) -> set[CertificateStatus]:
    return set(session.exec(select(Certificate.status).where(Certificate.tutor_id == tutor_id)).all())


def verified_types(session: Session, tutor_ids: list[UUID]) -> dict[UUID, list[CertificateType]]:
    """tutor id -> the certificate types an admin verified, for the public badges (R4.4)."""
    found: dict[UUID, list[CertificateType]] = defaultdict(list)
    if not tutor_ids:
        return found
    rows = session.exec(select(Certificate.tutor_id, Certificate.type).distinct().where(
        Certificate.tutor_id.in_(tutor_ids), Certificate.status == CertificateStatus.verified)).all()
    order = list(CertificateType)
    for tutor_id, kind in sorted(rows, key=lambda r: order.index(r[1])):
        found[tutor_id].append(kind)
    return found
