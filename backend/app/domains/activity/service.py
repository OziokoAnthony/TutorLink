"""Admin activity (spec 8). Routers call `record` after an admin action succeeds, so a refused action (an
HTTPException) writes nothing (R2.3)."""

from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.domains.activity.models import (
    ActivityKind,
    ActivityRead,
    AdminActivity,
    AdminDashboard,
    LastSession,
    TeamActivityRead,
)
from app.domains.auth.models import User, UserRole
from app.domains.notifications.service import naira  # noqa: F401  (re-exported for the routers' wording)

RECENT = 50  # R4.2
TEAM = 100  # R4.3


def record(session: Session, admin: User, text: str, kind: ActivityKind = ActivityKind.action) -> None:
    if admin.role != UserRole.admin:
        return
    session.add(AdminActivity(admin_id=admin.id, kind=kind, text=text))
    session.commit()


# ---------- Wording (R2.2) ----------

def percent(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}%"


def who(name: str | None, fallback: str = "a user") -> str:
    return name or fallback


# ---------- Reading ----------

def _reads(rows) -> list[ActivityRead]:
    return [ActivityRead.model_validate(r) for r in rows]


def dashboard(session: Session, admin: User) -> AdminDashboard:
    """R3, R4.1, R4.2: only the admin's own sessions and actions."""
    mine = select(AdminActivity).where(AdminActivity.admin_id == admin.id)
    logins = list(session.exec(mine.where(AdminActivity.kind == ActivityKind.login)
                               .order_by(AdminActivity.created_at.desc()).limit(2)).all())
    actions = mine.where(AdminActivity.kind == ActivityKind.action)
    last = None
    if len(logins) == 2:
        current, previous = logins
        rows = session.exec(actions.where(AdminActivity.created_at >= previous.created_at,
                                          AdminActivity.created_at < current.created_at)
                            .order_by(AdminActivity.created_at.desc())).all()
        last = LastSession(started_at=previous.created_at, ended_at=current.created_at, actions=_reads(rows))
    recent = session.exec(actions.order_by(AdminActivity.created_at.desc()).limit(RECENT)).all()
    return AdminDashboard(name=admin.name, email=admin.email, is_super_admin=admin.is_super_admin,
                          session_started_at=logins[0].created_at if logins else None,
                          last_session=last, recent=_reads(recent))


def team(session: Session, admin: User, admin_id: UUID | None = None) -> list[TeamActivityRead]:
    """R4.3, R4.4: the other admins' actions, for the super admin only."""
    if not admin.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the super admin can see other admins' activity")
    stmt = (select(AdminActivity, User).join(User, User.id == AdminActivity.admin_id)
            .where(AdminActivity.kind == ActivityKind.action, AdminActivity.admin_id != admin.id))
    if admin_id is not None:
        stmt = stmt.where(AdminActivity.admin_id == admin_id)
    rows = session.exec(stmt.order_by(AdminActivity.created_at.desc()).limit(TEAM)).all()
    return [TeamActivityRead(id=a.id, text=a.text, created_at=a.created_at, admin_id=u.id, admin_name=u.name,
                             admin_email=u.email) for a, u in rows]
