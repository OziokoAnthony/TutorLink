"""Subjects and legal pages (spec 7)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.activity import service as activity
from app.domains.auth.models import User, UserRole
from app.domains.content import service
from app.domains.content.models import (
    LegalIn,
    LegalKind,
    LegalRead,
    LegalVersion,
    SubjectAdminView,
    SubjectIn,
    SubjectOfferedIn,
    SubjectRead,
)

router = APIRouter(tags=["content"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles([UserRole.admin])


@router.get("/subjects", response_model=list[SubjectRead])
def subjects(session: Session = Depends(get_session)):
    """R1.6: public, because sign-up needs the list."""
    return service.offered_subjects(session)


@router.get("/legal/{kind}", response_model=LegalRead)
def legal(kind: LegalKind, session: Session = Depends(get_session)):
    return service.legal(session, kind)


@admin_router.get("/subjects", response_model=list[SubjectAdminView])
def admin_subjects(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.admin_subjects(session)


@admin_router.post("/subjects", response_model=SubjectAdminView, status_code=status.HTTP_201_CREATED)
def add_subject(data: SubjectIn, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    subject = service.add_subject(session, data)
    activity.record(session, admin, f"Added subject {subject.name}")
    return subject


@admin_router.patch("/subjects/{subject_id}", response_model=SubjectAdminView)
def set_offered(subject_id: UUID, data: SubjectOfferedIn, admin: User = Depends(admin_only),
                session: Session = Depends(get_session)):
    subject = service.set_offered(session, subject_id, data.is_offered)
    activity.record(session, admin, f"{'Restored' if data.is_offered else 'Removed'} subject {subject.name}")
    return subject


@admin_router.get("/legal/{kind}", response_model=list[LegalVersion])
def legal_versions(kind: LegalKind, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.legal_versions(session, kind)


@admin_router.post("/legal/{kind}", response_model=LegalRead, status_code=status.HTTP_201_CREATED)
def publish_legal(kind: LegalKind, data: LegalIn, admin: User = Depends(admin_only),
                  session: Session = Depends(get_session)):
    published = service.publish_legal(session, admin, kind, data)
    label = {"privacy": "privacy notice", "terms": "terms of service",
             "disclaimer": "disclaimer"}[kind.value]
    activity.record(session, admin, f"Published a new version of the {label}")
    return published
