from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.schedules import service
from app.domains.schedules.models import ScheduleCreate, ScheduleRead, TutorSlotRead

router = APIRouter(prefix="/schedules", tags=["schedules"])
tutor_router = APIRouter(prefix="/tutors", tags=["schedules"])

parent_only = require_roles([UserRole.parent])
tutor_only = require_roles([UserRole.tutor])


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(data: ScheduleCreate, parent: User = Depends(parent_only),
                    session: Session = Depends(get_session)):
    return service.create_schedule(session, parent, data)


@router.get("/me", response_model=list[ScheduleRead])
def my_schedules(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.list_my_schedules(session, parent)


@router.get("/tutor/me", response_model=list[ScheduleRead])
def my_tutor_schedules(tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.list_tutor_schedules(session, tutor)


@router.delete("/{schedule_id}", response_model=ScheduleRead)
def cancel_schedule(schedule_id: UUID, parent: User = Depends(parent_only),
                    session: Session = Depends(get_session)):
    return service.cancel_schedule(session, parent, schedule_id)


@tutor_router.get("/{tutor_id}/schedule", response_model=list[TutorSlotRead])
def tutor_schedule(tutor_id: UUID, user: User = Depends(get_current_user),
                   session: Session = Depends(get_session)):
    return service.get_tutor_slots(session, tutor_id)
