"""Public pages' data (spec 14): no login, nothing that identifies a tutor."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.domains.showcase import service
from app.domains.showcase.models import PublicLevel, PublicReview, PublicStats, PublicSubject, PublicSubjectDetail
from app.domains.tutors.models import EducationLevel

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stats", response_model=PublicStats)
def stats(session: Session = Depends(get_session)):
    return service.stats(session)


@router.get("/reviews", response_model=list[PublicReview])
def reviews(session: Session = Depends(get_session)):
    return service.reviews(session)


@router.get("/subjects", response_model=list[PublicSubject])
def subjects(session: Session = Depends(get_session)):
    return service.subjects(session)


@router.get("/subjects/{subject_slug}", response_model=PublicSubjectDetail)
def subject(subject_slug: str, session: Session = Depends(get_session)):
    return service.subject(session, subject_slug)


@router.get("/levels/{level}", response_model=PublicLevel)
def level(level: EducationLevel, session: Session = Depends(get_session)):
    return service.level(session, level)
