"""Parents and tutors at a glance, and removing accounts with notice (spec 10)."""

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, update
from sqlmodel import Session, select

from app.core import clock
from app.domains.auth.models import HeardFrom, ParentProfile, User, UserRole
from app.domains.bookings.models import Booking, BookingStatus
from app.domains.identity import service as identity
from app.domains.job_posts.models import JobPost, JobStatus
from app.domains.lessons.models import EarningStatus, Lesson, LessonStatus
from app.domains.notifications import service as notifications
from app.domains.notifications.service import date_text, naira
from app.domains.payments.models import WalletEntry
from app.domains.tutors.models import TutorProfile, VettingStatus
from app.domains.users.models import (
    Band,
    NoticeIn,
    RoleCounts,
    SourceCount,
    TutorStages,
    UserRow,
    UsersOverview,
)

ACTIVE = timedelta(days=90)  # R2.1
LONG = timedelta(days=180)
NOTICE = timedelta(days=14)  # R5.2
SEEN_EVERY = timedelta(hours=1)  # R1.1
PEOPLE = (UserRole.parent, UserRole.tutor)  # admins are never listed or removed here (R6.5)

OPEN_BOOKINGS = (BookingStatus.requested, BookingStatus.accepted, BookingStatus.active, BookingStatus.paused)
UNPAID = (EarningStatus.pending, EarningStatus.on_hold, EarningStatus.payable)
UNFINISHED = (LessonStatus.confirmed, LessonStatus.reported, LessonStatus.disputed, LessonStatus.flagged)


# ---------- Last seen (R1) ----------

def touch(session: Session, user: User) -> None:
    """Called on login and on every logged-in request; writes at most once an hour."""
    if user.role not in PEOPLE:
        return
    now = clock.now()
    if user.last_seen_at is None or now - user.last_seen_at >= SEEN_EVERY:
        user.last_seen_at = now
        session.add(user)
        session.commit()


# ---------- Bands (R2) ----------

def _seen():
    return func.coalesce(User.last_seen_at, User.created_at)


def _band_clause(band: Band, now):
    seen = _seen()
    live = and_(User.removed_at.is_(None), User.removal_due_at.is_(None))
    return {
        Band.active: and_(live, seen >= now - ACTIVE),
        Band.inactive: and_(live, seen < now - ACTIVE, seen >= now - LONG),
        Band.long_inactive: and_(live, seen < now - LONG),
        Band.notice: and_(User.removed_at.is_(None), User.removal_due_at.is_not(None)),
        Band.removed: User.removed_at.is_not(None),
    }[band]


def _band(user: User, now) -> Band:
    if user.removed_at is not None:
        return Band.removed
    if user.removal_due_at is not None:
        return Band.notice
    age = now - (user.last_seen_at or user.created_at)
    return Band.active if age < ACTIVE else Band.inactive if age < LONG else Band.long_inactive


# ---------- Overview and list (R3) ----------

def overview(session: Session) -> UsersOverview:
    now = clock.now()

    def counts(role: UserRole) -> RoleCounts:
        row = session.exec(select(func.count(), *[func.count().filter(_band_clause(b, now)) for b in Band])
                           .where(User.role == role)).one()
        return RoleCounts(registered=row[0], **{b.value: n for b, n in zip(Band, row[1:])})

    stages = dict(session.exec(select(TutorProfile.vetting_status, func.count())
                               .group_by(TutorProfile.vetting_status)).all())
    by_source: dict = {}
    for source, role, n in session.exec(select(User.heard_from, User.role, func.count())
                                        .where(User.role.in_(PEOPLE)).group_by(User.heard_from, User.role)).all():
        row = by_source.setdefault(source, {"parents": 0, "tutors": 0})
        row["parents" if role == UserRole.parent else "tutors"] += n
    order = [*HeardFrom, None]
    heard = [SourceCount(source=s, **by_source[s]) for s in order if s in by_source]
    return UsersOverview(parents=counts(UserRole.parent), tutors=counts(UserRole.tutor), heard_from=heard,
                         tutor_stages=TutorStages(onboarding=stages.get(VettingStatus.pending, 0),
                                                  approved=stages.get(VettingStatus.approved, 0),
                                                  rejected=stages.get(VettingStatus.rejected, 0)))


def _plural(n: int, word: str) -> str:
    return f"1 {word}" if n == 1 else f"{n} {word}s"


def outstanding(session: Session, users: list[User]) -> dict[UUID, list[str]]:
    """R4: what stops removing each account, in words. Four grouped queries for any number of accounts."""
    result: dict[UUID, list[str]] = {u.id: [] for u in users}
    parents = [u.id for u in users if u.role == UserRole.parent]
    tutors = [u.id for u in users if u.role == UserRole.tutor]
    if parents:
        for pid, total in session.exec(select(WalletEntry.parent_id, func.sum(WalletEntry.amount))
                                       .where(WalletEntry.parent_id.in_(parents))
                                       .group_by(WalletEntry.parent_id)).all():
            if clock.money(Decimal(total)) != 0:
                result[pid].append(f"{naira(clock.money(Decimal(total)))} balance")
        for pid, n in session.exec(select(Booking.parent_id, func.count())
                                   .where(Booking.parent_id.in_(parents), Booking.status.in_(OPEN_BOOKINGS))
                                   .group_by(Booking.parent_id)).all():
            result[pid].append(_plural(n, "unfinished booking"))
    if tutors:
        for tid, total in session.exec(select(Lesson.tutor_id, func.sum(Lesson.tutor_earning))
                                       .where(Lesson.tutor_id.in_(tutors), Lesson.earning_status.in_(UNPAID))
                                       .group_by(Lesson.tutor_id)).all():
            if total:
                result[tid].append(f"{naira(clock.money(Decimal(total)))} not paid yet")
        for tid, n in session.exec(select(Lesson.tutor_id, func.count())
                                   .where(Lesson.tutor_id.in_(tutors), Lesson.status.in_(UNFINISHED))
                                   .group_by(Lesson.tutor_id)).all():
            result[tid].append(_plural(n, "lesson") + " not finished")
    return result


def _rows(session: Session, found: list[tuple[User, str | None, TutorProfile | None]]) -> list[UserRow]:
    now = clock.now()
    owed = outstanding(session, [u for u, _, _ in found])
    return [UserRow(id=u.id, role=u.role, name=name, email=u.email, joined_at=u.created_at,
                    last_seen_at=u.last_seen_at or u.created_at, band=_band(u, now),
                    vetting_status=profile.vetting_status if profile else None,
                    nin_overdue=profile is not None and identity.nin_overdue(profile, now),  # spec 11 R4.3
                    outstanding=owed[u.id], removal_due_at=u.removal_due_at, removal_reason=u.removal_reason,
                    ready_to_remove=u.removal_due_at is not None and now >= u.removal_due_at,
                    removed_at=u.removed_at)
            for u, name, profile in found]


def _people():
    name = func.coalesce(ParentProfile.full_name, TutorProfile.full_name)
    stmt = (select(User, name, TutorProfile)
            .outerjoin(ParentProfile, ParentProfile.user_id == User.id)
            .outerjoin(TutorProfile, TutorProfile.user_id == User.id)
            .where(User.role.in_(PEOPLE)))
    return stmt, name


def list_users(session: Session, role: UserRole | None, band: Band | None, vetting: VettingStatus | None,
               q: str | None, skip: int, limit: int) -> list[UserRow]:
    """R3.3: newest sign-ups first."""
    stmt, name = _people()
    if role is not None:
        stmt = stmt.where(User.role == role)
    if band is not None:
        stmt = stmt.where(_band_clause(band, clock.now()))
    if vetting is not None:
        stmt = stmt.where(TutorProfile.vetting_status == vetting)
    if q and q.strip():
        term = q.strip()
        stmt = stmt.where(User.email.icontains(term, autoescape=True) | name.icontains(term, autoescape=True))
    found = session.exec(stmt.order_by(User.created_at.desc(), User.id).offset(skip).limit(limit)).all()
    return _rows(session, list(found))


def _person(session: Session, user_id: UUID) -> tuple[User, UserRow]:
    stmt, _ = _people()
    found = session.exec(stmt.where(User.id == user_id)).first()
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found")
    return found[0], _rows(session, [found])[0]


def _refuse_if_owed(row: UserRow) -> None:
    if row.outstanding:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"This account can't be removed while it has: {', '.join(row.outstanding)}. "
                            "Settle these first.")


# ---------- Notice, removal, restore (R5, R6) ----------

def send_notice(session: Session, user_id: UUID, data: NoticeIn) -> UserRow:
    user, row = _person(session, user_id)
    if user.removed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already removed")
    if user.removal_due_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A removal notice is already running for this account")
    _refuse_if_owed(row)
    now = clock.now()
    reason = " ".join(data.reason.split())
    user.removal_noticed_at, user.removal_due_at, user.removal_reason = now, now + NOTICE, reason
    session.add(user)
    notifications.notify(
        session, user.id, "Your TutorLink account will be closed",
        f"We plan to close your TutorLink account on {date_text(user.removal_due_at.astimezone(clock.WAT).date())}.\n"
        f"Reason: {reason}\n"
        "If you want to keep your account, reply through Help & feedback in your dashboard before then.",
        f"/dashboard/{user.role.value}/feedback")
    session.commit()
    return _person(session, user_id)[1]


def cancel_notice(session: Session, user_id: UUID) -> UserRow:
    user, _ = _person(session, user_id)
    if user.removal_due_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "There's no removal notice to cancel")
    user.removal_noticed_at = user.removal_due_at = user.removal_reason = None
    session.add(user)
    notifications.notify(session, user.id, "Your TutorLink account will stay open",
                         "We've cancelled the plan to close your account. Thank you for staying with TutorLink.",
                         f"/dashboard/{user.role.value}", email=False)
    session.commit()
    return _person(session, user_id)[1]


def remove(session: Session, user_id: UUID) -> UserRow:
    """R6.1-R6.3: after the notice, and only with nothing outstanding."""
    user, row = _person(session, user_id)
    if user.removed_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already removed")
    if user.removal_due_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Send a removal notice first")
    if clock.now() < user.removal_due_at:
        due = date_text(user.removal_due_at.astimezone(clock.WAT).date())
        raise HTTPException(status.HTTP_409_CONFLICT, f"The notice runs until {due}; you can remove it after that.")
    _refuse_if_owed(row)
    reason = user.removal_reason
    user.is_active = False
    user.removed_at = clock.now()
    user.removal_noticed_at = user.removal_due_at = None
    user.token_version += 1  # ends every session
    session.add(user)
    if user.role == UserRole.parent:
        session.exec(update(JobPost).where(JobPost.parent_id == user.id,
                                           JobPost.status.in_([JobStatus.open, JobStatus.pending, JobStatus.rejected]))
                     .values(status=JobStatus.closed))
    notifications.notify(session, user.id, "Your TutorLink account has been closed",
                         f"Your TutorLink account has been closed. Reason: {reason}\n"
                         "Your booking and payment records are kept. If you think this is a mistake, reply to "
                         "this email.")
    session.commit()
    return _person(session, user_id)[1]


def restore(session: Session, user_id: UUID) -> UserRow:
    """R6.4: they log in again with the same password."""
    user, _ = _person(session, user_id)
    if user.removed_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account isn't removed")
    user.is_active = True
    user.removed_at = None
    user.removal_reason = None
    session.add(user)
    notifications.notify(session, user.id, "Your TutorLink account is open again",
                         "Your TutorLink account has been restored. You can log in as before.", "/login")
    session.commit()
    return _person(session, user_id)[1]
