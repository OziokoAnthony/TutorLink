from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.sessions import service
from app.domains.sessions.models import SessionCreate, SessionRead, SessionStatus

router = APIRouter(prefix="/sessions", tags=["sessions"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

parent_only = require_roles([UserRole.parent])
tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


class SessionFilters:
    def __init__(
        self,
        status: SessionStatus | None = None,
        month: int | None = Query(None, ge=1, le=12),
        year: int | None = Query(None, ge=2000, le=2100),
    ):
        self.status = status
        self.month = month
        self.year = year


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def log_session(data: SessionCreate, tutor: User = Depends(tutor_only),
                session: Session = Depends(get_session)):
    return service.log_session(session, tutor, data)


@router.get("/me", response_model=list[SessionRead])
def my_sessions(filters: SessionFilters = Depends(), parent: User = Depends(parent_only),
                session: Session = Depends(get_session)):
    return service.list_parent_sessions(session, parent, filters.status, filters.month, filters.year)


@router.get("/tutor/me", response_model=list[SessionRead])
def my_tutor_sessions(filters: SessionFilters = Depends(), tutor: User = Depends(tutor_only),
                      session: Session = Depends(get_session)):
    return service.list_tutor_sessions(session, tutor, filters.status, filters.month, filters.year)


@router.patch("/{session_id}/confirm", response_model=SessionRead)
def confirm_session(session_id: UUID, parent: User = Depends(parent_only),
                    session: Session = Depends(get_session)):
    return service.confirm_session(session, parent, session_id)


@router.patch("/{session_id}/cancel", response_model=SessionRead)
def cancel_session(session_id: UUID, parent: User = Depends(parent_only),
                   session: Session = Depends(get_session)):
    return service.cancel_session(session, parent, session_id)


@admin_router.get("/sessions", response_model=list[SessionRead])
def all_sessions(
    filters: SessionFilters = Depends(),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    return service.list_all_sessions(session, filters.status, filters.month, filters.year, skip, limit)
