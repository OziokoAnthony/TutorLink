from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum, utcnow


class VettingStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EducationLevel(str, Enum):
    primary = "primary"
    junior_secondary = "junior_secondary"
    senior_secondary = "senior_secondary"


# Shared by tutor_subjects.level and schedules.level (one PostgreSQL type).
education_level_enum = pg_enum(EducationLevel, "education_level")


# ---------- Tables ----------

class TutorProfile(BaseUUIDModel, table=True):
    __tablename__ = "tutor_profiles"

    user_id: UUID = Field(foreign_key="users.id", unique=True)
    full_name: str
    phone: str | None = None
    bio: str | None = Field(default=None, sa_type=sa.Text)
    area: str
    rate_per_session: Decimal = Field(max_digits=10, decimal_places=2)
    vetting_status: VettingStatus = Field(
        default=VettingStatus.pending,
        sa_type=pg_enum(VettingStatus, "vetting_status"),
        sa_column_kwargs={"server_default": VettingStatus.pending.value},
    )
    vetting_note: str | None = Field(default=None, sa_type=sa.Text)
    vetted_by: UUID | None = Field(default=None, foreign_key="users.id")
    vetted_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


class TutorSubject(SQLModel, table=True):
    """Spec defines no updated_at here, so this table doesn't use BaseUUIDModel."""

    __tablename__ = "tutor_subjects"
    __table_args__ = (sa.UniqueConstraint("tutor_profile_id", "subject", "level"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tutor_profile_id: UUID = Field(foreign_key="tutor_profiles.id")
    subject: str
    level: EducationLevel = Field(sa_type=education_level_enum)
    created_at: datetime = Field(default_factory=utcnow, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class TutorProfileUpsert(SQLModel):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    bio: str | None = None
    area: str = Field(min_length=1, max_length=120)
    rate_per_session: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class TutorSubjectCreate(SQLModel):
    subject: str = Field(min_length=1, max_length=100)
    level: EducationLevel


class TutorSubjectRead(SQLModel):
    id: UUID
    subject: str
    level: EducationLevel


class TutorProfileRead(SQLModel):
    """Full profile, for the tutor themself and admins."""

    id: UUID
    user_id: UUID
    full_name: str
    phone: str | None
    bio: str | None
    area: str
    rate_per_session: Decimal
    vetting_status: VettingStatus
    vetting_note: str | None
    vetted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    subjects: list[TutorSubjectRead] = []
    average_rating: Decimal | None = None  # 1.00-5.00, None until first rating
    rating_count: int = 0


class TutorPublic(SQLModel):
    """Public listing shape: no contact or vetting details."""

    id: UUID
    user_id: UUID
    full_name: str
    bio: str | None
    area: str
    rate_per_session: Decimal
    subjects: list[TutorSubjectRead] = []
    average_rating: Decimal | None = None  # 1.00-5.00, None until first rating
    rating_count: int = 0


class VetRequest(SQLModel):
    status: Literal["approved", "rejected"]
    note: str | None = None
