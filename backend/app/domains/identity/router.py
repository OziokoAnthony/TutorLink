"""ID documents before the NIN (spec 11): tutors upload, admins verify or reject."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.activity import service as activity
from app.domains.auth.models import User, UserRole
from app.domains.identity import service
from app.domains.identity.models import (
    ID_LABELS,
    IdDocumentAdminView,
    IdDocumentStatus,
    IdDocumentTutorView,
    IdDocumentType,
    IdReviewIn,
)

router = APIRouter(prefix="/id-documents", tags=["onboarding"])
admin_router = APIRouter(prefix="/admin/id-documents", tags=["admin"])

tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.get("", response_model=list[IdDocumentTutorView])
def my_id_documents(user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.list_mine(session, user)


@router.post("", response_model=IdDocumentTutorView, status_code=status.HTTP_201_CREATED)
def upload_id_document(type: IdDocumentType = Form(...), file: UploadFile = File(...),
                       user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """A NIN slip, voter's card, driver's licence or international passport: PDF, JPG or PNG up to 10 MB (R1.1)."""
    return service.upload(session, user, type, file)


@admin_router.get("", response_model=list[IdDocumentAdminView])
def list_id_documents(status_filter: IdDocumentStatus | None = Query(None, alias="status"),
                      tutor_id: UUID | None = None,
                      admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.admin_list(session, status_filter, tutor_id)


@admin_router.patch("/{doc_id}", response_model=IdDocumentAdminView)
def review_id_document(doc_id: UUID, data: IdReviewIn, admin: User = Depends(admin_only),
                       session: Session = Depends(get_session)):
    """Verify, or reject with a note the tutor sees (R1.2)."""
    doc = service.review(session, admin, doc_id, data)
    verb = "Verified" if data.status == IdDocumentStatus.verified else "Rejected"
    tutor = f"{doc.tutor_first_name} {doc.tutor_surname}"
    activity.record(session, admin, f"{verb} the {ID_LABELS[doc.type]} of tutor {tutor}")  # R4.2
    return doc
