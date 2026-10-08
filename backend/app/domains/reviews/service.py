from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.domains.auth.models import ParentProfile, User
from app.domains.reviews.models import PublicReview, ReviewRead, ReviewUpsert, TutorReview, TutorToRate
from app.domains.lessons.models import Lesson, LessonStatus
from app.domains.tutors.models import TutorProfile, VettingStatus

RatingStats = tuple[Decimal | None, int]  # (average rating to 2 dp, number of ratings)


def rating_stats_subquery():
    """Per-tutor average and count, for joining onto tutor queries (e.g. sort by rating)."""
    return (
        select(
            TutorReview.tutor_id.label("tutor_id"),
            func.avg(TutorReview.rating).label("average_rating"),
            func.count().label("rating_count"),
        )
        .group_by(TutorReview.tutor_id)
        .subquery()
    )


def rating_stats(session: Session, tutor_ids: list[UUID]) -> dict[UUID, RatingStats]:
    if not tutor_ids:
        return {}
    rows = session.exec(
        select(TutorReview.tutor_id, func.avg(TutorReview.rating), func.count())
        .where(TutorReview.tutor_id.in_(tutor_ids))
        .group_by(TutorReview.tutor_id)
    ).all()
    return {
        tutor_id: (Decimal(avg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), count)
        for tutor_id, avg, count in rows
    }


def completed_lesson_count(session: Session, parent_id: UUID, tutor_id: UUID) -> int:
    return session.exec(
        select(func.count())
        .select_from(Lesson)
        .where(Lesson.parent_id == parent_id, Lesson.tutor_id == tutor_id, Lesson.status == LessonStatus.completed)
    ).one()


def has_reviewed(session: Session, parent_id: UUID, tutor_id: UUID) -> bool:
    return session.exec(
        select(TutorReview.id).where(TutorReview.parent_id == parent_id, TutorReview.tutor_id == tutor_id)
    ).first() is not None


def upsert_review(session: Session, parent: User, tutor_user_id: UUID, data: ReviewUpsert) -> ReviewRead:
    profile = session.exec(select(TutorProfile).where(TutorProfile.user_id == tutor_user_id)).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    if completed_lesson_count(session, parent.id, tutor_user_id) == 0:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "You can only rate a tutor after a completed lesson with them")

    comment = (data.comment or "").strip() or None
    review = session.exec(
        select(TutorReview).where(TutorReview.parent_id == parent.id, TutorReview.tutor_id == tutor_user_id)
    ).first()
    if review is None:
        review = TutorReview(tutor_id=tutor_user_id, parent_id=parent.id, rating=data.rating, comment=comment)
    else:
        review.rating = data.rating
        review.comment = comment
    session.add(review)
    try:
        session.commit()
    except IntegrityError:  # two simultaneous first reviews from the same parent
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Review was just submitted; please retry")
    session.refresh(review)
    return ReviewRead.model_validate(review)


def list_public_reviews(session: Session, tutor_user_id: UUID, skip: int, limit: int) -> list[PublicReview]:
    approved = session.exec(
        select(TutorProfile.id).where(
            TutorProfile.user_id == tutor_user_id, TutorProfile.vetting_status == VettingStatus.approved
        )
    ).first()
    if approved is None:  # same visibility as GET /tutors/{id} (business rule 2)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")

    rows = session.exec(
        select(TutorReview, ParentProfile.full_name)
        .outerjoin(ParentProfile, ParentProfile.user_id == TutorReview.parent_id)
        .where(TutorReview.tutor_id == tutor_user_id)
        .order_by(TutorReview.updated_at.desc(), TutorReview.id)
        .offset(skip)
        .limit(limit)
    ).all()
    return [
        PublicReview(
            rating=review.rating,
            comment=review.comment,
            parent_first_name=(full_name or "Parent").split()[0],
            created_at=review.created_at,
            updated_at=review.updated_at,
        )
        for review, full_name in rows
    ]


def tutors_to_rate(session: Session, parent_id: UUID) -> list[TutorToRate]:
    """Tutors this parent has had a completed lesson with but hasn't rated yet."""
    not_reviewed = ~(
        select(TutorReview.id)
        .where(TutorReview.parent_id == parent_id, TutorReview.tutor_id == Lesson.tutor_id)
        .exists()
    )
    rows = session.exec(
        select(Lesson.tutor_id, TutorProfile.full_name)
        .join(TutorProfile, TutorProfile.user_id == Lesson.tutor_id)
        .where(Lesson.parent_id == parent_id, Lesson.status == LessonStatus.completed, not_reviewed)
        .distinct()
        .order_by(TutorProfile.full_name)
    ).all()
    return [TutorToRate(tutor_id=tutor_id, full_name=full_name) for tutor_id, full_name in rows]
