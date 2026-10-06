import calendar
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db.base import utcnow
from app.domains.auth.models import ParentProfile, User
from app.domains.notifications import service as notifications
from app.domains.reviews import service as review_service
from app.domains.tutors.models import TutorProfile
from app.domains.schedules.models import Schedule
from app.domains.sessions.models import SessionCreate, SessionRead, SessionStatus, TutoringSession

# Nigeria is UTC+1 all year (no DST). "Today" for session logging is the tutor's local day.
WAT = timezone(timedelta(hours=1), "WAT")


def today_in_nigeria() -> date:
    return datetime.now(WAT).date()


def _filtered(stmt, status_: SessionStatus | None, month: int | None, year: int | None):
    if status_:
        stmt = stmt.where(TutoringSession.status == status_)
    if month:
        stmt = stmt.where(extract("month", TutoringSession.session_date) == month)
    if year:
        stmt = stmt.where(extract("year", TutoringSession.session_date) == year)
    return stmt.order_by(TutoringSession.session_date.desc(), TutoringSession.created_at.desc())


def _get_with_schedule(session: Session, session_id: UUID) -> tuple[TutoringSession, Schedule]:
    tutoring_session = session.get(TutoringSession, session_id)
    if tutoring_session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return tutoring_session, session.get(Schedule, tutoring_session.schedule_id)


def log_session(session: Session, tutor: User, data: SessionCreate) -> SessionRead:
    schedule = session.get(Schedule, data.schedule_id)
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    if schedule.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not the tutor for this schedule")
    if data.session_date > today_in_nigeria():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "session_date cannot be in the future")
    if data.session_date.weekday() != schedule.day_of_week:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"session_date must be a {calendar.day_name[schedule.day_of_week]} for this schedule")
    # Lessons taught before a schedule was cancelled can still be logged (and billed), later ones can't.
    # Schedules are never edited after booking, so updated_at on an inactive schedule is its cancellation time.
    if not schedule.is_active and data.session_date > schedule.updated_at.astimezone(WAT).date():
        raise HTTPException(status.HTTP_409_CONFLICT, "Schedule was cancelled before this date")

    already_logged = session.exec(
        select(TutoringSession.id).where(
            TutoringSession.schedule_id == schedule.id,
            TutoringSession.session_date == data.session_date,
        )
    ).first()
    if already_logged:
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already logged for this date")

    tutoring_session = TutoringSession(
        **data.model_dump(),
        status=SessionStatus.logged,
        logged_by=tutor.id,
        logged_at=utcnow(),
    )
    session.add(tutoring_session)
    try:
        session.commit()
    except IntegrityError:  # concurrent duplicate
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Session already logged for this date")
    session.refresh(tutoring_session)

    parent = session.get(User, schedule.parent_id)
    profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent.id)).first()
    notifications.session_logged(parent.email, profile.full_name if profile else "there", schedule.subject,
                                 tutoring_session.session_date, tutoring_session.topic_covered)
    return SessionRead.model_validate(tutoring_session)


def list_parent_sessions(session: Session, parent: User, status_: SessionStatus | None,
                         month: int | None, year: int | None) -> list[SessionRead]:
    stmt = (
        select(TutoringSession)
        .join(Schedule, Schedule.id == TutoringSession.schedule_id)
        .where(Schedule.parent_id == parent.id)
    )
    return [SessionRead.model_validate(s) for s in session.exec(_filtered(stmt, status_, month, year)).all()]


def list_tutor_sessions(session: Session, tutor: User, status_: SessionStatus | None,
                        month: int | None, year: int | None) -> list[SessionRead]:
    stmt = (
        select(TutoringSession)
        .join(Schedule, Schedule.id == TutoringSession.schedule_id)
        .where(Schedule.tutor_id == tutor.id)
    )
    return [SessionRead.model_validate(s) for s in session.exec(_filtered(stmt, status_, month, year)).all()]


def list_all_sessions(session: Session, status_: SessionStatus | None, month: int | None,
                      year: int | None, skip: int, limit: int) -> list[SessionRead]:
    stmt = _filtered(select(TutoringSession), status_, month, year).offset(skip).limit(limit)
    return [SessionRead.model_validate(s) for s in session.exec(stmt).all()]


def confirm_session(session: Session, parent: User, session_id: UUID) -> SessionRead:
    tutoring_session, schedule = _get_with_schedule(session, session_id)
    if schedule.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only confirm your own sessions")
    if tutoring_session.status != SessionStatus.logged:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Only logged sessions can be confirmed (status is '{tutoring_session.status.value}')")

    tutoring_session.status = SessionStatus.confirmed
    tutoring_session.confirmed_by = parent.id
    tutoring_session.confirmed_at = utcnow()
    session.add(tutoring_session)
    session.commit()
    session.refresh(tutoring_session)

    if review_service.should_prompt_for_rating(session, parent.id, schedule.tutor_id):
        parent_profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent.id)).first()
        tutor_profile = session.exec(select(TutorProfile).where(TutorProfile.user_id == schedule.tutor_id)).first()
        notifications.rate_tutor_prompt(parent.email, parent_profile.full_name if parent_profile else "there",
                                        tutor_profile.full_name if tutor_profile else "your tutor")
    return SessionRead.model_validate(tutoring_session)


def cancel_session(session: Session, parent: User, session_id: UUID) -> SessionRead:
    tutoring_session, schedule = _get_with_schedule(session, session_id)
    if schedule.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only cancel your own sessions")
    if tutoring_session.status not in (SessionStatus.scheduled, SessionStatus.logged):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Session cannot be cancelled (status is '{tutoring_session.status.value}')")

    tutoring_session.status = SessionStatus.cancelled
    session.add(tutoring_session)
    session.commit()
    session.refresh(tutoring_session)
    return SessionRead.model_validate(tutoring_session)
