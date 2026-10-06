from datetime import datetime, time
from uuid import UUID

import sqlalchemy as sa
from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel
from app.domains.tutors.models import EducationLevel, education_level_enum


# ---------- Tables ----------

class Schedule(BaseUUIDModel, table=True):
    __tablename__ = "schedules"
    __table_args__ = (
        # Fast clash detection (CLAUDE.md business rule 3).
        sa.Index("ix_schedules_tutor_id_day_of_week_is_active", "tutor_id", "day_of_week", "is_active"),
    )

    tutor_id: UUID = Field(foreign_key="users.id")
    parent_id: UUID = Field(foreign_key="users.id", index=True)
    day_of_week: int = Field(sa_type=sa.SmallInteger)  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time
    subject: str
    level: EducationLevel = Field(sa_type=education_level_enum)
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": sa.true()})


# ---------- DTOs ----------

class ScheduleCreate(SQLModel):
    tutor_id: UUID
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    subject: str = Field(min_length=1, max_length=100)
    level: EducationLevel

    @model_validator(mode="after")
    def check_times(self) -> "ScheduleCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ScheduleRead(SQLModel):
    id: UUID
    tutor_id: UUID
    parent_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    subject: str
    level: EducationLevel
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TutorSlotRead(SQLModel):
    """A tutor's booked slot as anyone can see it, without the parent's identity."""

    id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    subject: str
    level: EducationLevel
