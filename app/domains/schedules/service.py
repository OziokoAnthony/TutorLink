from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.domains.auth.models import ParentProfile, User, UserRole
from app.domains.notifications import service as notifications
from app.domains.schedules.models import Schedule, ScheduleCreate, ScheduleRead, TutorSlotRead
from app.domains.tutors import service as tutor_service
from app.domains.tutors.models import TutorProfile


def _parent_name(session: Session, parent_id: UUID) -> str:
    profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent_id)).first()
    return profile.full_name if profile else "there"


def _notify_recipients(session: Session, schedule: Schedule) -> list[tuple[str, str]]:
    parent = session.get(User, schedule.parent_id)
    tutor = session.get(User, schedule.tutor_id)
    tutor_profile: TutorProfile | None = tutor_service.get_profile_by_user_id(session, tutor.id)
    return [
        (parent.email, _parent_name(session, parent.id)),
        (tutor.email, tutor_profile.full_name if tutor_profile else "there"),
    ]


def has_clash(session: Session, tutor_id: UUID, day_of_week: int, start_time, end_time) -> bool:
    """CLAUDE.md business rule 3: overlapping active slot for the same tutor on the same day."""
    return session.exec(
        select(Schedule.id)
        .where(
            Schedule.tutor_id == tutor_id,
            Schedule.day_of_week == day_of_week,
            Schedule.is_active == True,  # noqa: E712
            Schedule.start_time < end_time,
            Schedule.end_time > start_time,
        )
        .limit(1)
    ).first() is not None


def create_schedule(session: Session, parent: User, data: ScheduleCreate) -> ScheduleRead:
    # Lock the tutor's row so two concurrent bookings can't both pass the clash check.
    tutor = session.exec(
        select(User)
        .where(User.id == data.tutor_id, User.role == UserRole.tutor, User.is_active == True)  # noqa: E712
        .with_for_update()
    ).first()
    profile = tutor and tutor_service.get_approved_profile(session, tutor.id)
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    if not tutor_service.teaches(session, profile, data.subject, data.level):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Tutor does not teach this subject at this level")
    if has_clash(session, tutor.id, data.day_of_week, data.start_time, data.end_time):
        raise HTTPException(status.HTTP_409_CONFLICT, "Tutor already has a session at this time.")

    schedule = Schedule(parent_id=parent.id, subject=data.subject.strip(),
                        **data.model_dump(exclude={"subject"}))
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    notifications.schedule_booked(_notify_recipients(session, schedule), schedule.subject,
                                  schedule.day_of_week, schedule.start_time, schedule.end_time)
    return ScheduleRead.model_validate(schedule)


def list_my_schedules(session: Session, parent: User) -> list[ScheduleRead]:
    schedules = session.exec(
        select(Schedule)
        .where(Schedule.parent_id == parent.id, Schedule.is_active == True)  # noqa: E712
        .order_by(Schedule.day_of_week, Schedule.start_time)
    ).all()
    return [ScheduleRead.model_validate(s) for s in schedules]


def cancel_schedule(session: Session, parent: User, schedule_id: UUID) -> ScheduleRead:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Schedule not found")
    if schedule.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only cancel your own schedules")
    if not schedule.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Schedule is already cancelled")

    schedule.is_active = False
    session.add(schedule)
    session.commit()
    session.refresh(schedule)

    notifications.schedule_cancelled(_notify_recipients(session, schedule), schedule.subject,
                                     schedule.day_of_week, schedule.start_time)
    return ScheduleRead.model_validate(schedule)


def get_tutor_slots(session: Session, tutor_user_id: UUID) -> list[TutorSlotRead]:
    tutor = session.get(User, tutor_user_id)
    if tutor is None or tutor.role != UserRole.tutor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    schedules = session.exec(
        select(Schedule)
        .where(Schedule.tutor_id == tutor_user_id, Schedule.is_active == True)  # noqa: E712
        .order_by(Schedule.day_of_week, Schedule.start_time)
    ).all()
    return [TutorSlotRead.model_validate(s) for s in schedules]
