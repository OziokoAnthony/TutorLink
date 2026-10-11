"""Tutor ratings. `{tutor_id}` is the tutor's user id, as everywhere else."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.deps import can_see_tutors, require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.reviews import service
from app.domains.reviews.models import PublicReview, ReviewRead, ReviewUpsert

router = APIRouter(prefix="/tutors", tags=["reviews"])

parent_only = require_roles([UserRole.parent])


@router.put("/{tutor_id}/reviews", response_model=ReviewRead)
def rate_tutor(tutor_id: UUID, data: ReviewUpsert, parent: User = Depends(parent_only),
               session: Session = Depends(get_session)):
    """Create or update my rating of this tutor (one per parent per tutor)."""
    return service.upsert_review(session, parent, tutor_id, data)


@router.get("/{tutor_id}/reviews", response_model=list[PublicReview])
def tutor_reviews(
    tutor_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    viewer: User = Depends(can_see_tutors),
    session: Session = Depends(get_session),
):
    return service.list_public_reviews(session, tutor_id, skip, limit)
