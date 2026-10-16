"""The admin dashboard and team activity (spec 8 R4)."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.activity import service
from app.domains.activity.models import AdminDashboard, TeamActivityRead
from app.domains.auth.models import User, UserRole

admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles([UserRole.admin])


@admin_router.get("/dashboard", response_model=AdminDashboard)
def dashboard(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.dashboard(session, admin)


@admin_router.get("/activity", response_model=list[TeamActivityRead])
def team_activity(admin_id: UUID | None = None, admin: User = Depends(admin_only),
                  session: Session = Depends(get_session)):
    """Super admin only: other admins' actions, optionally one admin's (R4.3, R4.4)."""
    return service.team(session, admin, admin_id)
