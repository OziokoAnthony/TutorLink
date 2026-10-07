from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.db.base import utcnow
from app.domains.auth import photos as photos_service
from app.domains.auth.models import User
from app.domains.notifications import service as notifications
from app.domains.reviews import service as review_service
from app.domains.tutors.models import (
    EducationLevel,
    OfferIn,
    OfferRead,
    TutorOffer,
    TutorOfferSubject,
    TutorOfferWindow,
    TutorProfile,
    TutorProfileRead,
    TutorProfileUpsert,
    TutorPublic,
    VetRequest,
    VettingStatus,
    WeeklyTime,
)


# ---------- Read helpers (also used by auth and bookings) ----------

def get_profile_by_user_id(session: Session, user_id: UUID) -> TutorProfile | None:
    return session.exec(select(TutorProfile).where(TutorProfile.user_id == user_id)).first()


def get_approved_profile(session: Session, user_id: UUID) -> TutorProfile | None:
    return session.exec(
        select(TutorProfile).where(
            TutorProfile.user_id == user_id,
            TutorProfile.vetting_status == VettingStatus.approved,
        )
    ).first()


def _offers_for(session: Session, tutor_ids: list[UUID]) -> dict[UUID, list[OfferRead]]:
    """tutor user id -> active offers with subjects and windows (three queries for any number of tutors)."""
    grouped: dict[UUID, list[OfferRead]] = defaultdict(list)
    if not tutor_ids:
        return grouped
    offers = session.exec(
        select(TutorOffer)
        .where(TutorOffer.tutor_id.in_(tutor_ids), TutorOffer.is_active == True)  # noqa: E712
        .order_by(TutorOffer.price, TutorOffer.created_at)
    ).all()
    offer_ids = [o.id for o in offers]
    subjects: dict[UUID, list[str]] = defaultdict(list)
    windows: dict[UUID, list[WeeklyTime]] = defaultdict(list)
    if offer_ids:
        for row in session.exec(select(TutorOfferSubject).where(TutorOfferSubject.offer_id.in_(offer_ids))
                                .order_by(TutorOfferSubject.subject)).all():
            subjects[row.offer_id].append(row.subject)
        for row in session.exec(select(TutorOfferWindow).where(TutorOfferWindow.offer_id.in_(offer_ids))
                                .order_by(TutorOfferWindow.day_of_week, TutorOfferWindow.start_time)).all():
            windows[row.offer_id].append(WeeklyTime.model_validate(row))
    for offer in offers:
        grouped[offer.tutor_id].append(OfferRead(id=offer.id, subjects=subjects[offer.id], level=offer.level,
                                                 windows=windows[offer.id], price=offer.price))
    return grouped


def _build(session: Session, profiles: list[TutorProfile], read_model):
    """Attach offers, photo and rating summary to each profile (a fixed number of queries per list)."""
    user_ids = [p.user_id for p in profiles]
    offers = _offers_for(session, user_ids)
    photos = photos_service.urls_for(session, user_ids)
    ratings = review_service.rating_stats(session, user_ids)
    return [
        read_model.model_validate(p, update={
            "offers": offers[p.user_id],
            "price_from": min((o.price for o in offers[p.user_id]), default=None),
            "photo_url": photos.get(p.user_id),
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


# ---------- Offers ----------

def get_offer(session: Session, offer_id: UUID) -> OfferRead | None:
    """An active offer with its subjects and windows."""
    offer = session.get(TutorOffer, offer_id)
    if offer is None or not offer.is_active:
        return None
    return next(o for o in _offers_for(session, [offer.tutor_id])[offer.tutor_id] if o.id == offer_id)


def add_offer_rows(session: Session, tutor_id: UUID, data: OfferIn) -> TutorOffer:
    """Adds an offer to the session without committing (registration uses it inside its own transaction)."""
    offer = TutorOffer(tutor_id=tutor_id, level=data.level, price=data.price)
    session.add(offer)
    session.flush()
    _write_children(session, offer.id, data)
    return offer


def _write_children(session: Session, offer_id: UUID, data: OfferIn) -> None:
    for subject in data.subjects:
        session.add(TutorOfferSubject(offer_id=offer_id, subject=subject))
    for window in data.windows:
        session.add(TutorOfferWindow(offer_id=offer_id, **window.model_dump()))


def _own_offer(session: Session, user: User, offer_id: UUID) -> TutorOffer:
    offer = session.get(TutorOffer, offer_id)
    if offer is None or not offer.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")
    if offer.tutor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only change your own offers")
    return offer


def list_my_offers(session: Session, user: User) -> list[OfferRead]:
    return _offers_for(session, [user.id])[user.id]


def create_offer(session: Session, user: User, data: OfferIn) -> OfferRead:
    offer = add_offer_rows(session, user.id, data)
    session.commit()
    return get_offer(session, offer.id)


def update_offer(session: Session, user: User, offer_id: UUID, data: OfferIn) -> OfferRead:
    """Replaces the offer's subjects, level, windows and price. Accepted bookings keep their own copy
    of what was agreed, so they are unaffected (spec 1 R0.3)."""
    offer = _own_offer(session, user, offer_id)
    offer.level = data.level
    offer.price = data.price
    session.add(offer)
    session.exec(delete(TutorOfferSubject).where(TutorOfferSubject.offer_id == offer.id))
    session.exec(delete(TutorOfferWindow).where(TutorOfferWindow.offer_id == offer.id))
    _write_children(session, offer.id, data)
    session.commit()
    return get_offer(session, offer.id)


def remove_offer(session: Session, user: User, offer_id: UUID) -> None:
    offer = _own_offer(session, user, offer_id)
    active_offers = session.exec(
        select(func.count()).select_from(TutorOffer)
        .where(TutorOffer.tutor_id == user.id, TutorOffer.is_active == True)  # noqa: E712
    ).one()
    if active_offers <= 1:
        raise HTTPException(status.HTTP_409_CONFLICT, "You need at least one offer")
    offer.is_active = False  # bookings may still point at it (spec 1 R0.4)
    session.add(offer)
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
        offer_filter = select(TutorOffer.id).where(
            TutorOffer.tutor_id == TutorProfile.user_id, TutorOffer.is_active == True,  # noqa: E712
        )
        if subject:
            offer_filter = offer_filter.where(
                select(TutorOfferSubject.id).where(
                    TutorOfferSubject.offer_id == TutorOffer.id,
                    func.lower(TutorOfferSubject.subject) == subject.strip().lower(),
                ).exists()
            )
        if level:
            offer_filter = offer_filter.where(TutorOffer.level == level)
        stmt = stmt.where(offer_filter.exists())
    if sort == "price":
        lowest = (
            select(func.min(TutorOffer.price))
            .where(TutorOffer.tutor_id == TutorProfile.user_id, TutorOffer.is_active == True)  # noqa: E712
            .scalar_subquery()
        )
        stmt = stmt.order_by(lowest.asc().nulls_last())
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
