from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import StringConstraints, model_validator
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.tutors.models import EducationLevel, WeeklyTime, clean_subjects, education_level_enum


class BookingStatus(str, Enum):
    requested = "requested"  # waiting for the tutor (72 h)
    accepted = "accepted"  # taken by the tutor, first period not paid yet
    active = "active"
    paused = "paused"  # a later period wasn't paid in time
    ended = "ended"
    declined = "declined"
    expired = "expired"  # the tutor didn't answer in time
    released = "released"  # the first period wasn't paid in time
    cancelled = "cancelled"  # by the parent


# Statuses in which a booking holds the tutor's time slots (spec 1 R2.2: accepted and active bookings).
HOLDS_SLOTS = (BookingStatus.accepted, BookingStatus.active, BookingStatus.paused)


class LessonMode(str, Enum):
    online = "online"
    offline = "offline"


class BillingPeriod(str, Enum):
    daily = "daily"  # each day with lessons is paid on its own
    weekly = "weekly"  # Monday-Sunday
    monthly = "monthly"  # calendar month


class PeriodStatus(str, Enum):
    due = "due"  # payable now, not paid yet
    paid = "paid"
    missed = "missed"  # a later period's deadline passed unpaid: booking paused
    expired = "expired"  # the first period's deadline passed unpaid: booking released
    void = "void"  # booking closed before it was paid


# ---------- Tables ----------

class Booking(BaseUUIDModel, table=True):
    __tablename__ = "bookings"

    parent_id: UUID = Field(foreign_key="users.id", index=True)
    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    offer_id: UUID | None = Field(default=None, foreign_key="tutor_offers.id")
    subjects: list[str] = Field(sa_type=ARRAY(sa.String))
    level: EducationLevel = Field(sa_type=education_level_enum)
    mode: LessonMode = Field(sa_type=pg_enum(LessonMode, "lesson_mode"))
    billing_period: BillingPeriod = Field(sa_type=pg_enum(BillingPeriod, "billing_period"))
    start_date: date
    end_date: date | None = None
    price: Decimal = Field(max_digits=10, decimal_places=2)  # agreed price per lesson (P)
    # Copied from platform_fees when the tutor accepts; never recalculated (spec 1 R1.1).
    parent_fee_rate: Decimal | None = Field(default=None, max_digits=5, decimal_places=4)
    tutor_fee_rate: Decimal | None = Field(default=None, max_digits=5, decimal_places=4)
    child_strengths: str = Field(sa_type=sa.Text)
    child_weaknesses: str = Field(sa_type=sa.Text)
    status: BookingStatus = Field(
        default=BookingStatus.requested,
        sa_type=pg_enum(BookingStatus, "booking_status"),
        sa_column_kwargs={"server_default": BookingStatus.requested.value},
    )
    responded_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    paused_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    closed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    close_note: str | None = Field(default=None, sa_type=sa.Text)


class BookingSlot(SQLModel, table=True):
    """A weekly lesson time of a booking."""

    __tablename__ = "booking_slots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    booking_id: UUID = Field(foreign_key="bookings.id", index=True)
    day_of_week: int = Field(sa_type=sa.SmallInteger)  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time


class BookingPeriod(BaseUUIDModel, table=True):
    """One prepaid billing period of a booking: its lessons and what the parent pays for them."""

    __tablename__ = "booking_periods"
    __table_args__ = (sa.UniqueConstraint("booking_id", "starts_on"),)

    booking_id: UUID = Field(foreign_key="bookings.id")  # covered by the unique constraint's index
    parent_id: UUID = Field(foreign_key="users.id", index=True)
    starts_on: date  # date of its first lesson
    ends_on: date  # last day the period covers
    lesson_count: int
    amount: Decimal = Field(max_digits=12, decimal_places=2)  # parent total, fee included
    first_lesson_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    last_lesson_end_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    due_at: datetime = Field(sa_type=sa.DateTime(timezone=True))  # 24 h before the first lesson
    status: PeriodStatus = Field(
        default=PeriodStatus.due,
        sa_type=pg_enum(PeriodStatus, "period_status"),
        sa_column_kwargs={"server_default": PeriodStatus.due.value},
    )
    paid_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    reminder_sent_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=1000)]


class BookingCreate(SQLModel):
    tutor_id: UUID
    offer_id: UUID
    subjects: list[Annotated[str, StringConstraints(max_length=100)]] = Field(min_length=1, max_length=10)
    slots: list[WeeklyTime] = Field(min_length=1, max_length=14)
    start_date: date
    end_date: date | None = None
    billing_period: BillingPeriod
    mode: LessonMode
    child_strengths: LongText
    child_weaknesses: LongText

    @model_validator(mode="after")
    def check(self) -> "BookingCreate":
        self.subjects = clean_subjects(self.subjects)
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class BookingClose(SQLModel):
    note: str | None = Field(default=None, max_length=1000)


class PeriodView(SQLModel):
    """A billing period as the parent (and admin) sees it."""

    id: UUID
    starts_on: date
    ends_on: date
    lesson_count: int
    amount: Decimal
    due_at: datetime
    status: PeriodStatus
    paid_at: datetime | None


class BookingBase(SQLModel):
    id: UUID
    parent_id: UUID
    tutor_id: UUID
    subjects: list[str]
    level: EducationLevel
    mode: LessonMode
    billing_period: BillingPeriod
    start_date: date
    end_date: date | None
    price: Decimal  # agreed price per lesson (P): everyone sees it
    child_strengths: str
    child_weaknesses: str
    status: BookingStatus
    slots: list[WeeklyTime] = []
    created_at: datetime
    responded_at: datetime | None
    closed_at: datetime | None
    close_note: str | None
    parent_name: str | None = None
    tutor_name: str | None = None
    parent_photo_url: str | None = None
    tutor_photo_url: str | None = None


class BookingParentView(BookingBase):
    """What the parent sees: their price per lesson, never the fee rates or the tutor's earning."""

    parent_price_per_lesson: Decimal  # fee included, shown as an amount only (spec 1 R1.2)
    periods: list[PeriodView] = []


class BookingTutorView(BookingBase):
    """What the tutor sees: their fee and earning, never the parent's fee or total."""

    tutor_fee_rate: Decimal
    tutor_earning_per_lesson: Decimal


class BookingAdminView(BookingBase):
    parent_fee_rate: Decimal
    tutor_fee_rate: Decimal
    parent_price_per_lesson: Decimal
    tutor_earning_per_lesson: Decimal
    platform_margin_per_lesson: Decimal
    periods: list[PeriodView] = []


class TutorSlotRead(SQLModel):
    """A tutor's booked weekly time, without who booked it."""

    day_of_week: int
    start_time: time
    end_time: time


class TutorAvailability(SQLModel):
    """What parents see before booking, so they don't pick a time the tutor is already teaching."""

    in_session_now: bool  # the tutor is teaching a lesson right now
    busy: list[TutorSlotRead]  # weekly times already booked
    free: list[TutorSlotRead]  # weekly times the tutor offers that are still open
