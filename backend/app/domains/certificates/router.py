"""Certificates (spec 4 R4): tutors upload, admins verify or reject."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.certificates import service
from app.domains.certificates.models import (
    CertificateAdminView,
    CertificateFields,
    CertificateStatus,
    CertificateTutorView,
    CertificateType,
    ReviewRequest,
)

router = APIRouter(prefix="/certificates", tags=["certificates"])
admin_router = APIRouter(prefix="/admin/certificates", tags=["admin"])

tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


def certificate_fields(
    type: CertificateType = Form(...),
    institution: str = Form(...),
    year: int = Form(...),
    exam_number: str | None = Form(None),
    exam_year: int | None = Form(None),
    checker_pin: str | None = Form(None),
) -> CertificateFields:
    try:
        return CertificateFields(type=type, institution=institution, year=year, exam_number=exam_number,
                                 exam_year=exam_year, checker_pin=checker_pin)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors())


@router.get("", response_model=list[CertificateTutorView])
def my_certificates(user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.list_mine(session, user)


@router.post("", response_model=CertificateTutorView, status_code=status.HTTP_201_CREATED)
def upload_certificate(file: UploadFile = File(...), fields: CertificateFields = Depends(certificate_fields),
                       user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """A PDF, JPG or PNG up to 10 MB. WAEC and NECO also need the exam number, exam year and
    result-checker PIN (R4.2). Allowed once the tutor's NIN is verified."""
    return service.upload(session, user, fields, file)


@admin_router.get("", response_model=list[CertificateAdminView])
def list_certificates(status_filter: CertificateStatus | None = Query(None, alias="status"),
                      tutor_id: UUID | None = None,
                      admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Oldest first. `?status=pending` is the review queue; `?tutor_id=` one tutor's certificates."""
    return service.admin_list(session, status_filter, tutor_id)


@admin_router.patch("/{certificate_id}", response_model=CertificateAdminView)
def review_certificate(certificate_id: UUID, data: ReviewRequest, admin: User = Depends(admin_only),
                       session: Session = Depends(get_session)):
    """Verify or reject (with a note the tutor sees). The checker PIN is erased either way (R4.2, R4.3)."""
    return service.review(session, admin, certificate_id, data)
