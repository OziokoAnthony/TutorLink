from datetime import date, datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.tutors.models import EducationLevel


class SessionStatus(str, Enum):
    scheduled = "scheduled"
    logged = "logged"
    confirmed = "confirmed"
    cancelled = "cancelled"


# ---------- Tables ----------

class TutoringSession(BaseUUIDModel, table=True):
    """The `sessions` table. Named TutoringSession to avoid clashing with the DB `Session`."""

    __tablename__ = "sessions"
    __table_args__ = (sa.UniqueConstraint("schedule_id", "session_date"),)

    schedule_id: UUID = Field(foreign_key="schedules.id")
    session_date: date
    topic_covered: str | None = Field(default=None, sa_type=sa.Text)
    homework: str | None = Field(default=None, sa_type=sa.Text)
    status: SessionStatus = Field(
        default=SessionStatus.scheduled,
        sa_type=pg_enum(SessionStatus, "session_status"),
        sa_column_kwargs={"server_default": SessionStatus.scheduled.value},
    )
    logged_by: UUID | None = Field(default=None, foreign_key="users.id")
    logged_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    confirmed_by: UUID | None = Field(default=None, foreign_key="users.id")
    confirmed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class SessionCreate(SQLModel):
    schedule_id: UUID
    session_date: date
    topic_covered: str | None = None
    homework: str | None = None


class SessionRead(SQLModel):
    id: UUID
    schedule_id: UUID
    session_date: date
    topic_covered: str | None
    homework: str | None
    status: SessionStatus
    logged_by: UUID | None
    logged_at: datetime | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # From the schedule, so session lists can show "Mathematics, Tutor: Amara" without extra calls.
    subject: str | None = None
    level: EducationLevel | None = None
    tutor_id: UUID | None = None
    tutor_name: str | None = None
    parent_name: str | None = None
