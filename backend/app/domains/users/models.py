"""Parents and tutors at a glance, and removing accounts with notice (spec 10). No tables of its own: the state
lives on `users` (last_seen_at, removal_*, removed_at)."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.domains.auth.models import UserRole
from app.domains.tutors.models import VettingStatus


class Band(str, Enum):
    """R2: by last seen; a notice or a removal replaces the band."""

    active = "active"  # seen within 90 days
    inactive = "inactive"  # 90-180 days
    long_inactive = "long_inactive"  # over 180 days ("inactive for a while")
    notice = "notice"  # a removal notice is running
    removed = "removed"


class RoleCounts(SQLModel):
    registered: int
    active: int
    inactive: int
    long_inactive: int
    notice: int
    removed: int


class TutorStages(SQLModel):
    onboarding: int  # not approved yet
    approved: int
    rejected: int


class UsersOverview(SQLModel):
    """R3.1, R3.2."""

    parents: RoleCounts
    tutors: RoleCounts
    tutor_stages: TutorStages


class UserRow(SQLModel):
    """R3.3."""

    id: UUID
    role: UserRole
    name: str | None
    email: str
    joined_at: datetime
    last_seen_at: datetime  # sign-up time until they're seen (R1.2)
    band: Band
    vetting_status: VettingStatus | None  # tutors only
    outstanding: list[str]  # R4.3, e.g. "₦20,000.00 balance"; removing needs it empty
    removal_due_at: datetime | None
    removal_reason: str | None
    ready_to_remove: bool  # the notice ran out (R6.1)
    removed_at: datetime | None


class NoticeIn(SQLModel):
    reason: str = Field(min_length=10, max_length=1000)  # R5.1
