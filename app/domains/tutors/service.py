from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.base import utcnow
from app.domains.auth.models import User
from app.domains.notifications import service as notifications
from app.domains.reviews import service as review_service
from app.domains.tutors.models import (
    EducationLevel,
    TutorProfile,
    TutorProfileRead,
    TutorProfileUpsert,
    TutorPublic,
    TutorSubject,
    TutorSubjectCreate,
    TutorSubjectRead,
    VetRequest,
    VettingStatus,
)


# ---------- Read helpers (also used by auth, schedules and billing) ----------

def get_profile_by_user_id(session: Session, user_id: UUID) -> TutorProfile | None:
    return session.exec(select(TutorProfile).where(TutorProfile.user_id == user_id)).first()


def get_approved_profile(session: Session, user_id: UUID) -> TutorProfile | None:
    return session.exec(
        select(TutorProfile).where(
            TutorProfile.user_id == user_id,
            TutorProfile.vetting_status == VettingStatus.approved,
        )
    ).first()


def teaches(session: Session, profile: TutorProfile, subject: str, level: EducationLevel) -> bool:
    return session.exec(
        select(TutorSubject.id).where(
            TutorSubject.tutor_profile_id == profile.id,
            func.lower(TutorSubject.subject) == subject.strip().lower(),
            TutorSubject.level == level,
        )
    ).first() is not None


def _subjects_for(session: Session, profile_ids: list[UUID]) -> dict[UUID, list[TutorSubjectRead]]:
    grouped: dict[UUID, list[TutorSubjectRead]] = defaultdict(list)
    if not profile_ids:
        return grouped
    rows = session.exec(
        select(TutorSubject)
        .where(TutorSubject.tutor_profile_id.in_(profile_ids))
        .order_by(TutorSubject.subject, TutorSubject.level)
    ).all()
    for row in rows:
        grouped[row.tutor_profile_id].append(TutorSubjectRead.model_validate(row))
    return grouped


def _build(session: Session, profiles: list[TutorProfile], read_model):
    """Attach subjects and rating summary to each profile (two queries, whatever the list size)."""
    subjects = _subjects_for(session, [p.id for p in profiles])
    ratings = review_service.rating_stats(session, [p.user_id for p in profiles])
    return [
        read_model.model_validate(p, update={
            "subjects": subjects[p.id],
            "average_rating": ratings.get(p.user_id, (None, 0))[0],
            "rating_count": ratings.get(p.user_id, (None, 0))[1],
        })
        for p in profiles
    ]


def build_profile_read(session: Session, profile: TutorProfile) -> TutorProfileRead:
    return _build(session, [profile], TutorProfileRead)[0]


def _build_public_list(session: Session, profiles: list[TutorProfile]) -> list[TutorPublic]:
    return _build(session, profiles, TutorPublic)


# ---------- Tutor self-service ----------

def upsert_profile(session: Session, user: User, data: TutorProfileUpsert) -> TutorProfileRead:
    profile = get_profile_by_user_id(session, user.id)
    if profile is None:
        profile = TutorProfile(user_id=user.id, **data.model_dump())
    else:
        for field, value in data.model_dump().items():
            setattr(profile, field, value)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return build_profile_read(session, profile)


def _require_own_profile(session: Session, user: User) -> TutorProfile:
    profile = get_profile_by_user_id(session, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Create your tutor profile first")
    return profile


def add_subject(session: Session, user: User, data: TutorSubjectCreate) -> TutorSubjectRead:
    profile = _require_own_profile(session, user)
    subject_name = data.subject.strip()
    if teaches(session, profile, subject_name, data.level):
        raise HTTPException(status.HTTP_409_CONFLICT, "Subject already added at this level")

    subject = TutorSubject(tutor_profile_id=profile.id, subject=subject_name, level=data.level)
    session.add(subject)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Subject already added at this level")
    session.refresh(subject)
    return TutorSubjectRead.model_validate(subject)


def remove_subject(session: Session, user: User, subject_id: UUID) -> None:
    subject = session.get(TutorSubject, subject_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")
    profile = get_profile_by_user_id(session, user.id)
    if profile is None or subject.tutor_profile_id != profile.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only remove your own subjects")
    session.delete(subject)
    session.commit()


# ---------- Public listing ----------

def list_approved_tutors(
    session: Session,
    subject: str | None,
    level: EducationLevel | None,
    area: str | None,
    skip: int,
    limit: int,
    sort: str = "name",
) -> list[TutorPublic]:
    stmt = select(TutorProfile).where(TutorProfile.vetting_status == VettingStatus.approved)
    if area:
        stmt = stmt.where(TutorProfile.area.icontains(area.strip(), autoescape=True))
    if subject or level:
        teaches_filter = select(TutorSubject.id).where(TutorSubject.tutor_profile_id == TutorProfile.id)
        if subject:
            teaches_filter = teaches_filter.where(func.lower(TutorSubject.subject) == subject.strip().lower())
        if level:
            teaches_filter = teaches_filter.where(TutorSubject.level == level)
        stmt = stmt.where(teaches_filter.exists())
    if sort == "rating":
        # Best average first; ties go to the tutor with more ratings; unrated tutors last.
        stats = review_service.rating_stats_subquery()
        stmt = stmt.outerjoin(stats, stats.c.tutor_id == TutorProfile.user_id).order_by(
            stats.c.average_rating.desc().nulls_last(), stats.c.rating_count.desc().nulls_last(),
        )
    stmt = stmt.order_by(TutorProfile.full_name, TutorProfile.id).offset(skip).limit(limit)
    return _build_public_list(session, list(session.exec(stmt).all()))


def get_public_tutor(session: Session, tutor_user_id: UUID) -> TutorPublic:
    profile = get_approved_profile(session, tutor_user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    return _build_public_list(session, [profile])[0]


# ---------- Admin ----------

def vet_tutor(session: Session, admin: User, tutor_user_id: UUID, data: VetRequest) -> TutorProfileRead:
    profile = get_profile_by_user_id(session, tutor_user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")

    profile.vetting_status = VettingStatus(data.status)
    profile.vetting_note = data.note
    profile.vetted_by = admin.id
    profile.vetted_at = utcnow()
    session.add(profile)
    session.commit()
    session.refresh(profile)

    tutor = session.get(User, tutor_user_id)
    if profile.vetting_status == VettingStatus.approved:
        notifications.tutor_approved(tutor.email, profile.full_name)
    else:
        notifications.tutor_rejected(tutor.email, profile.full_name, profile.vetting_note)
    return build_profile_read(session, profile)


def list_pending_tutors(session: Session) -> list[TutorProfileRead]:
    profiles = session.exec(
        select(TutorProfile)
        .where(TutorProfile.vetting_status == VettingStatus.pending)
        .order_by(TutorProfile.created_at)
    ).all()
    return _build(session, list(profiles), TutorProfileRead)
