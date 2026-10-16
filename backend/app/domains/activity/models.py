"""Admin activity log (spec 8): one plain-English line per admin action, and a line per login."""

from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel


class ActivityKind(str, Enum):
    login = "login"  # starts a session (R3.1)
    action = "action"


# ---------- Tables ----------

class AdminActivity(BaseUUIDModel, table=True):
    """Written when it happens and never edited, so a line keeps the names it had then (R2.2, R2.3)."""

    __tablename__ = "admin_activity"
    __table_args__ = (sa.Index("ix_admin_activity_admin_id_created_at", "admin_id", "created_at"),)

    admin_id: UUID = Field(foreign_key="users.id")
    kind: ActivityKind = Field(sa_type=sa.String(10))
    text: str = Field(sa_type=sa.Text)


# ---------- DTOs ----------

class ActivityRead(SQLModel):
    id: UUID
    text: str
    created_at: datetime


class TeamActivityRead(ActivityRead):
    """Only the super admin reads these (R4.3)."""

    admin_id: UUID
    admin_name: str | None
    admin_email: str


class LastSession(SQLModel):
    started_at: datetime
    ended_at: datetime  # when the current session started
    actions: list[ActivityRead]  # newest first; empty means nothing changed


class AdminDashboard(SQLModel):
    name: str | None  # None until they set it: greet by email (R1.3)
    email: str
    is_super_admin: bool
    session_started_at: datetime | None
    last_session: LastSession | None  # None on a first login (R3.2)
    recent: list[ActivityRead]  # their latest 50 actions
