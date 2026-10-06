"""Tutor endpoints. `{tutor_id}` in every path is the tutor's *user* id (users.id), the same id
schedules, sessions and invoice items use to reference a tutor."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.tutors import service
from app.domains.tutors.models import (
    EducationLevel,
    TutorProfileRead,
    TutorProfileUpsert,
    TutorPublic,
    TutorSubjectCreate,
    TutorSubjectRead,
    VetRequest,
)

router = APIRouter(prefix="/tutors", tags=["tutors"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.post("/profile", response_model=TutorProfileRead)
def upsert_profile(data: TutorProfileUpsert, user: User = Depends(tutor_only),
                   session: Session = Depends(get_session)):
    return service.upsert_profile(session, user, data)


@router.post("/profile/subjects", response_model=TutorSubjectRead, status_code=status.HTTP_201_CREATED)
def add_subject(data: TutorSubjectCreate, user: User = Depends(tutor_only),
                session: Session = Depends(get_session)):
    return service.add_subject(session, user, data)


@router.delete("/profile/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_subject(subject_id: UUID, user: User = Depends(tutor_only),
                   session: Session = Depends(get_session)):
    service.remove_subject(session, user, subject_id)


@router.get("", response_model=list[TutorPublic])
def list_tutors(
    subject: str | None = None,
    level: EducationLevel | None = None,
    area: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: Literal["name", "rating"] = "name",
    session: Session = Depends(get_session),
):
    return service.list_approved_tutors(session, subject, level, area, skip, limit, sort)


@router.get("/{tutor_id}", response_model=TutorPublic)
def get_tutor(tutor_id: UUID, session: Session = Depends(get_session)):
    return service.get_public_tutor(session, tutor_id)


@router.patch("/{tutor_id}/vet", response_model=TutorProfileRead)
def vet_tutor(tutor_id: UUID, data: VetRequest, admin: User = Depends(admin_only),
              session: Session = Depends(get_session)):
    return service.vet_tutor(session, admin, tutor_id, data)


@admin_router.get("/tutors/pending", response_model=list[TutorProfileRead])
def list_pending(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.list_pending_tutors(session)
