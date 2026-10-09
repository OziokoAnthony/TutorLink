"""Job posts (spec 2): a parent describes what they need and at what price, and tutors apply."""

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
from app.domains.bookings.models import BillingPeriod, LessonMode, LongText
from app.domains.certificates.models import CertificateType, certificate_type_enum
from app.domains.tutors import subjects as subject_list
from app.domains.tutors.models import EducationLevel, WeeklyTime, clean_subjects, education_level_enum


class JobStatus(str, Enum):
    pending = "pending"  # posted or edited, waiting for an admin to review it; tutors can't see it (R1.4)
    rejected = "rejected"  # an admin turned it down with a note; the parent can edit it to resubmit
    open = "open"  # approved: tutors can see and apply; no time limit
    ongoing = "ongoing"  # a tutor was chosen; its booking is awaiting payment or active
    completed = "completed"  # that booking ended
    closed = "closed"  # the parent closed it while open


class ApplicationStatus(str, Enum):
    applied = "applied"
    withdrawn = "withdrawn"  # by the tutor, or automatically when an edit made it clash (R1.3)
    chosen = "chosen"


# ---------- Tables ----------

class JobPost(BaseUUIDModel, table=True):
    __tablename__ = "job_posts"

    parent_id: UUID = Field(foreign_key="users.id", index=True)
    subjects: list[str] = Field(sa_type=ARRAY(sa.String))
    level: EducationLevel = Field(sa_type=education_level_enum)
    mode: LessonMode = Field(sa_type=pg_enum(LessonMode, "lesson_mode"))
    area: str | None = None  # required for offline lessons
    billing_period: BillingPeriod = Field(sa_type=pg_enum(BillingPeriod, "billing_period"))
    start_date: date
    end_date: date | None = None
    price: Decimal = Field(max_digits=10, decimal_places=2)  # P, set by the parent
    qualifications: str = Field(sa_type=sa.Text)
    min_certificate: CertificateType | None = Field(default=None,
                                                    sa_type=certificate_type_enum)
    other_requirements: str | None = Field(default=None, sa_type=sa.Text)
    child_strengths: str = Field(sa_type=sa.Text)
    child_weaknesses: str = Field(sa_type=sa.Text)
    recording_consent_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))  # online only
    recording_consent_text: str | None = Field(default=None, sa_type=sa.Text)
    status: JobStatus = Field(default=JobStatus.pending, sa_type=pg_enum(JobStatus, "job_status"),
                              sa_column_kwargs={"server_default": JobStatus.pending.value})
    review_note: str | None = Field(default=None, sa_type=sa.Text)  # why an admin rejected it
    reviewed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    # While ongoing or completed. bookings.job_id points back here, so this key is created separately
    # (use_alter) to break the cycle between the two tables.
    booking_id: UUID | None = Field(default=None, sa_column=sa.Column(
        sa.Uuid, sa.ForeignKey("bookings.id", use_alter=True, name="fk_job_posts_booking_id_bookings")))
    closed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


class JobSlot(SQLModel, table=True):
    """A weekly lesson time the parent wants."""

    __tablename__ = "job_slots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    job_id: UUID = Field(foreign_key="job_posts.id", index=True)
    day_of_week: int = Field(sa_type=sa.SmallInteger)  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time


class JobApplication(BaseUUIDModel, table=True):
    __tablename__ = "job_applications"
    __table_args__ = (sa.UniqueConstraint("job_id", "tutor_id"),)  # one application per tutor per job (R2.6)

    job_id: UUID = Field(foreign_key="job_posts.id")  # covered by the unique constraint's index
    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    note: str | None = Field(default=None, sa_type=sa.Text)
    status: ApplicationStatus = Field(default=ApplicationStatus.applied,
                                      sa_type=pg_enum(ApplicationStatus, "application_status"),
                                      sa_column_kwargs={"server_default": ApplicationStatus.applied.value})
    withdrawn_reason: str | None = Field(default=None, sa_type=sa.Text)


# ---------- DTOs ----------

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class JobIn(SQLModel):
    """Posting a job, or replacing an open job's details (R1.1, R1.3)."""

    subjects: list[Annotated[str, StringConstraints(max_length=100)]] = Field(min_length=1, max_length=10)
    level: EducationLevel
    mode: LessonMode
    area: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    slots: list[WeeklyTime] = Field(min_length=1, max_length=14)
    start_date: date
    end_date: date | None = None
    billing_period: BillingPeriod
    qualifications: ShortText
    min_certificate: CertificateType | None = None
    other_requirements: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    child_strengths: LongText
    child_weaknesses: LongText
    recording_consent: bool = False  # required for online lessons (spec 3 R1.4)

    @model_validator(mode="after")
    def check(self) -> "JobIn":
        self.subjects = subject_list.listed(clean_subjects(self.subjects))
        if self.mode == LessonMode.offline and not self.area:
            raise ValueError("area is required for offline lessons")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class JobReviewIn(SQLModel):
    """An admin's decision on a pending job (R1.4)."""

    status: JobStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check(self) -> "JobReviewIn":
        if self.status not in (JobStatus.open, JobStatus.rejected):
            raise ValueError("status must be 'open' (approve) or 'rejected'")
        self.note = (self.note or "").strip() or None
        if self.status == JobStatus.rejected and not self.note:
            raise ValueError("say why the job is rejected, so the parent can fix it")
        return self


class ApplicationIn(SQLModel):
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class ApplicationTutorView(SQLModel):
    id: UUID
    job_id: UUID
    note: str | None
    status: ApplicationStatus
    withdrawn_reason: str | None
    created_at: datetime


class JobBase(SQLModel):
    id: UUID
    subjects: list[str]
    level: EducationLevel
    mode: LessonMode
    area: str | None
    slots: list[WeeklyTime] = []
    start_date: date
    end_date: date | None
    billing_period: BillingPeriod
    qualifications: str
    min_certificate: CertificateType | None
    other_requirements: str | None
    price: Decimal  # P: everyone sees it
    child_strengths: str
    child_weaknesses: str
    status: JobStatus
    created_at: datetime


class JobParentView(JobBase):
    """The parent's own job: their price per lesson, never the tutor fee or earning."""

    parent_price_per_lesson: Decimal  # fee included, as an amount only (spec 1 R1.2)
    booking_id: UUID | None
    applicant_count: int = 0
    review_note: str | None  # why it was rejected


class JobAdminView(JobBase):
    """A job in the admin review queue: who posted it, and the review so far (R1.4)."""

    parent_id: UUID
    parent_name: str | None
    review_note: str | None
    reviewed_at: datetime | None
    updated_at: datetime


class JobTutorView(JobBase):
    """A job as a tutor sees it: their fee and earning, the parent's first name and picture only (R2.3, R2.4)."""

    tutor_fee_rate: Decimal
    tutor_earning_per_lesson: Decimal
    parent_first_name: str
    parent_photo_url: str | None = None
    my_application: ApplicationTutorView | None = None


class ApplicantView(SQLModel):
    """An applicant as the parent sees them; the full profile is GET /tutors/{tutor_id} (R3.1)."""

    id: UUID
    tutor_id: UUID
    tutor_name: str | None
    tutor_photo_url: str | None
    average_rating: Decimal | None = None
    rating_count: int = 0
    note: str | None
    status: ApplicationStatus
    created_at: datetime
