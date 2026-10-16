"""Subjects and legal pages (spec 7), and agreeing to them (spec 9)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.activity import service as activity
from app.domains.auth import limits
from app.domains.auth.models import User, UserRole
from app.domains.content import service
from app.domains.content.models import (
    AcceptLegalIn,
    LegalAudience,
    LegalIn,
    LegalKind,
    LegalRead,
    LegalVersion,
    MyLegal,
    SubjectAdminView,
    SubjectIn,
    SubjectOfferedIn,
    SubjectRead,
)

router = APIRouter(tags=["content"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles([UserRole.admin])
parent_or_tutor = require_roles([UserRole.parent, UserRole.tutor])


@router.get("/subjects", response_model=list[SubjectRead])
def subjects(session: Session = Depends(get_session)):
    """R1.6: public, because sign-up needs the list."""
    return service.offered_subjects(session)


@router.get("/legal/me", response_model=MyLegal)
def my_legal(user: User = Depends(parent_or_tutor), session: Session = Depends(get_session)):
    """Spec 9 R2.4: the reader's own three documents, whether they've agreed, and whether they must now."""
    return service.my_legal(session, user)


@router.post("/legal/me/accept", response_model=MyLegal)
def accept_legal(data: AcceptLegalIn, request: Request, user: User = Depends(parent_or_tutor),
                 session: Session = Depends(get_session)):
    """Spec 9 R2.1-R2.3: agree to the latest version of all three documents."""
    return service.accept_legal(session, user, data, limits.client_ip(request))


@router.get("/legal/{kind}", response_model=LegalRead)
def legal(kind: LegalKind, audience: LegalAudience = LegalAudience.parent, session: Session = Depends(get_session)):
    """Public: the parents' version unless the tutors' is asked for (spec 9 R1.3)."""
    return service.legal(session, audience, kind)


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


@admin_router.get("/legal/{audience}/{kind}", response_model=list[LegalVersion])
def legal_versions(audience: LegalAudience, kind: LegalKind, admin: User = Depends(admin_only),
                   session: Session = Depends(get_session)):
    return service.legal_versions(session, audience, kind)


@admin_router.post("/legal/{audience}/{kind}", response_model=LegalRead, status_code=status.HTTP_201_CREATED)
def publish_legal(audience: LegalAudience, kind: LegalKind, data: LegalIn, admin: User = Depends(admin_only),
                  session: Session = Depends(get_session)):
    published = service.publish_legal(session, admin, audience, kind, data)
    activity.record(session, admin, f"Published a new version of the {service.AUDIENCE_WORDS[audience]} "
                                    f"{service.LEGAL_TITLES[kind]}")  # spec 9 R6.2
    return published
