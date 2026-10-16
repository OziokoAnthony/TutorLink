"""Parents and tutors at a glance, and removing accounts with notice (spec 10)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.activity import service as activity
from app.domains.auth.models import User, UserRole
from app.domains.tutors.models import VettingStatus
from app.domains.users import service
from app.domains.users.models import Band, NoticeIn, UserRow, UsersOverview

admin_router = APIRouter(prefix="/admin/users", tags=["admin"])

admin_only = require_roles([UserRole.admin])


def _who(row: UserRow) -> str:
    return f"{row.role.value} {row.name or row.email}"


@admin_router.get("/overview", response_model=UsersOverview)
def overview(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.overview(session)


@admin_router.get("", response_model=list[UserRow])
def list_users(role: UserRole | None = None, band: Band | None = None, vetting: VettingStatus | None = None,
               q: str | None = Query(default=None, max_length=100), skip: int = Query(default=0, ge=0),
               limit: int = Query(default=50, ge=1, le=200), admin: User = Depends(admin_only),
               session: Session = Depends(get_session)):
    return service.list_users(session, role, band, vetting, q, skip, limit)


@admin_router.post("/{user_id}/notice", response_model=UserRow)
def send_notice(user_id: UUID, data: NoticeIn, admin: User = Depends(admin_only),
                session: Session = Depends(get_session)):
    row = service.send_notice(session, user_id, data)
    activity.record(session, admin, f"Sent a removal notice to {_who(row)}")
    return row


@admin_router.delete("/{user_id}/notice", response_model=UserRow)
def cancel_notice(user_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    row = service.cancel_notice(session, user_id)
    activity.record(session, admin, f"Cancelled the removal notice for {_who(row)}")
    return row


@admin_router.post("/{user_id}/remove", response_model=UserRow)
def remove(user_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    row = service.remove(session, user_id)
    activity.record(session, admin, f"Removed {_who(row)}")
    return row


@admin_router.post("/{user_id}/restore", response_model=UserRow)
def restore(user_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    row = service.restore(session, user_id)
    activity.record(session, admin, f"Restored {_who(row)}")
    return row
