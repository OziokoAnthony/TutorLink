"""What visitors see before signing up (spec 14). Read-only. Only bookable tutors count (R1.2), and no response
names, shows or identifies a tutor (R1.1)."""

import re
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.auth.models import ParentProfile
from app.domains.content.models import Subject
from app.domains.fees import service as fees
from app.domains.lessons.models import Lesson, LessonStatus
from app.domains.reviews.models import TutorReview
from app.domains.showcase.models import (
    LevelPrices,
    LevelSubject,
    PublicLevel,
    PublicReview,
    PublicStats,
    PublicSubject,
    PublicSubjectDetail,
)
from app.domains.tutors import service as tutors
from app.domains.tutors.models import EducationLevel, TutorOffer, TutorOfferSubject, TutorProfile

MIN_OFFERS = 3  # R4.2: with fewer offers, a range would show one tutor's price
REVIEWS = 6  # R3.2


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _subjects(session: Session) -> list[Subject]:
    return list(session.exec(select(Subject).where(Subject.is_offered == True)  # noqa: E712
                             .order_by(Subject.group, Subject.name)).all())


def _offers(session: Session) -> list[tuple[str, EducationLevel, Decimal, UUID]]:
    """(subject key, level, price, tutor id) for every active offer of a bookable tutor."""
    rows = session.exec(
        select(TutorOfferSubject.subject, TutorOffer.level, TutorOffer.price, TutorOffer.tutor_id)
        .join(TutorOffer, TutorOffer.id == TutorOfferSubject.offer_id)
        .join(TutorProfile, TutorProfile.user_id == TutorOffer.tutor_id)
        .where(TutorOffer.is_active == True, tutors.bookable())  # noqa: E712
    ).all()
    return [(" ".join(name.lower().split()), level, price, tutor) for name, level, price, tutor in rows]


def _range(prices: list[Decimal], rate: Decimal) -> tuple[Decimal | None, Decimal | None]:
    if len(prices) < MIN_OFFERS:
        return None, None
    return fees.parent_price(min(prices), rate), fees.parent_price(max(prices), rate)


def stats(session: Session) -> PublicStats:
    """R2.1."""
    tutor_count = session.exec(select(func.count()).select_from(TutorProfile).where(tutors.bookable())).one()
    lessons = session.exec(select(func.count()).select_from(Lesson)
                           .where(Lesson.status == LessonStatus.completed)).one()
    average, count = session.exec(select(func.avg(TutorReview.rating), func.count(TutorReview.id))).one()
    return PublicStats(verified_tutors=tutor_count, lessons_taught=lessons,
                       average_rating=round(float(average), 1) if average is not None else None,
                       rating_count=count)


def reviews(session: Session, tutor_ids: set[UUID] | None = None, limit: int = REVIEWS) -> list[PublicReview]:
    """R3: 4 and 5 stars with a comment, newest first; only the parent's first name."""
    stmt = (select(TutorReview.rating, TutorReview.comment, TutorReview.created_at, ParentProfile.full_name)
            .join(ParentProfile, ParentProfile.user_id == TutorReview.parent_id)
            .where(TutorReview.rating >= 4, TutorReview.comment.is_not(None),
                   func.trim(TutorReview.comment) != ""))
    if tutor_ids is not None:
        if not tutor_ids:
            return []
        stmt = stmt.where(TutorReview.tutor_id.in_(tutor_ids))
    rows = session.exec(stmt.order_by(TutorReview.created_at.desc()).limit(limit)).all()
    return [PublicReview(first_name=(name.split() or ["A parent"])[0], rating=rating, comment=comment.strip(),
                         created_at=created) for rating, comment, created, name in rows]


def subjects(session: Session) -> list[PublicSubject]:
    """R4.1: every offered subject with how many bookable tutors teach it."""
    teaching: dict[str, set[UUID]] = defaultdict(set)
    for key, _, _, tutor in _offers(session):
        teaching[key].add(tutor)
    return [PublicSubject(slug=slug(s.name), name=s.name, group=s.group, tutors=len(teaching[s.key]))
            for s in _subjects(session)]


def subject(session: Session, subject_slug: str) -> PublicSubjectDetail:
    """R4.2-R4.4."""
    found = next((s for s in _subjects(session) if slug(s.name) == subject_slug), None)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")
    rate = fees.current(session).parent_fee_rate
    by_level: dict[EducationLevel, list[tuple[Decimal, UUID]]] = defaultdict(list)
    for key, level, price, tutor in _offers(session):
        if key == found.key:
            by_level[level].append((price, tutor))
    levels = []
    for level in EducationLevel:
        if level in by_level:
            low, high = _range([p for p, _ in by_level[level]], rate)
            levels.append(LevelPrices(level=level, tutors=len({t for _, t in by_level[level]}),
                                      min_price=low, max_price=high))
    teachers = {t for offers in by_level.values() for _, t in offers}
    return PublicSubjectDetail(slug=slug(found.name), name=found.name, group=found.group, tutors=len(teachers),
                               levels=levels, reviews=reviews(session, teachers))


def level(session: Session, level_: EducationLevel) -> PublicLevel:
    """R5.1: the subjects taught at a level, each with its tutor count and price range."""
    rate = fees.current(session).parent_fee_rate
    prices: dict[str, list[tuple[Decimal, UUID]]] = defaultdict(list)
    for key, lvl, price, tutor in _offers(session):
        if lvl == level_:
            prices[key].append((price, tutor))
    items = []
    for s in _subjects(session):
        if s.key in prices:
            low, high = _range([p for p, _ in prices[s.key]], rate)
            items.append(LevelSubject(slug=slug(s.name), name=s.name, group=s.group,
                                      tutors=len({t for _, t in prices[s.key]}), min_price=low, max_price=high))
    return PublicLevel(level=level_, tutors=len({t for offers in prices.values() for _, t in offers}),
                       subjects=items)
