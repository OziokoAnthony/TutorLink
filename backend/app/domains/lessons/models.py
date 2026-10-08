from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from pydantic import StringConstraints, model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.bookings.models import LessonMode
from app.domains.tutors.models import EducationLevel


class LessonStatus(str, Enum):
    confirmed = "confirmed"  # paid for and on the timetable
    reported = "reported"  # tutor submitted the report; parent's 24 h problem window is open
    completed = "completed"  # window closed without a problem (or admin rejected the problem)
    disputed = "disputed"  # a problem is open
    flagged = "flagged"  # no report within 24 h of the lesson: possible absence, admin reviews
    refunded = "refunded"  # admin refunded it after a problem
    cancelled = "cancelled"  # parent cancelled with 48 h notice; refund requested


class EarningStatus(str, Enum):
    pending = "pending"  # lesson not finished yet
    on_hold = "on_hold"  # a problem or missing report is being reviewed
    payable = "payable"
    paid = "paid"  # included in a payout (a failed transfer makes it payable again)
    void = "void"  # refunded or cancelled lesson: nothing to pay


class IssueKind(str, Enum):
    tutor_absent = "tutor_absent"
    late_or_left_early = "late_or_left_early"
    agreement_broken = "agreement_broken"
    other = "other"
    no_report = "no_report"  # raised automatically when the tutor doesn't report in time


class IssueResolution(str, Enum):
    refund = "refund"
    reschedule = "reschedule"
    reject = "reject"


# ---------- Tables ----------

class Lesson(BaseUUIDModel, table=True):
    """One paid lesson. Amounts are copied from the booking when its period is paid."""

    __tablename__ = "lessons"
    __table_args__ = (sa.UniqueConstraint("booking_id", "starts_at"),)

    booking_id: UUID = Field(foreign_key="bookings.id")  # covered by the unique constraint's index
    period_id: UUID = Field(foreign_key="booking_periods.id", index=True)
    parent_id: UUID = Field(foreign_key="users.id", index=True)
    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    lesson_date: date
    start_time: time
    end_time: time
    starts_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    ends_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    status: LessonStatus = Field(
        default=LessonStatus.confirmed,
        sa_type=pg_enum(LessonStatus, "lesson_status"),
        sa_column_kwargs={"server_default": LessonStatus.confirmed.value},
    )
    topic_covered: str | None = Field(default=None, sa_type=sa.Text)
    homework: str | None = Field(default=None, sa_type=sa.Text)
    reported_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    problem_window_ends_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    price: Decimal = Field(max_digits=10, decimal_places=2)  # P
    parent_price: Decimal = Field(max_digits=10, decimal_places=2)  # P x (1 + S)
    tutor_earning: Decimal = Field(max_digits=10, decimal_places=2)  # P x (1 - T)
    earning_status: EarningStatus = Field(
        default=EarningStatus.pending,
        sa_type=pg_enum(EarningStatus, "earning_status"),
        sa_column_kwargs={"server_default": EarningStatus.pending.value},
    )
    payable_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    payout_due_at: datetime = Field(sa_type=sa.DateTime(timezone=True))  # 48 h after the period's last lesson
    payout_id: UUID | None = Field(default=None, foreign_key="payouts.id", index=True)
    # Online lessons (spec 3 R2): the recording the tutor uploads straight to storage before reporting.
    recording_key: str | None = None  # set when an upload link is issued
    recording_content_type: str | None = None
    recording_size: int | None = Field(default=None, sa_type=sa.BigInteger)
    recording_uploaded_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    recording_deleted_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


class LessonIssue(BaseUUIDModel, table=True):
    """A problem with a lesson, reported by the parent or raised automatically (no report)."""

    __tablename__ = "lesson_issues"

    lesson_id: UUID = Field(foreign_key="lessons.id", index=True)
    raised_by: UUID | None = Field(default=None, foreign_key="users.id")  # None: raised automatically
    kind: IssueKind = Field(sa_type=pg_enum(IssueKind, "issue_kind"))
    description: str | None = Field(default=None, sa_type=sa.Text)
    resolution: IssueResolution | None = Field(default=None, sa_type=pg_enum(IssueResolution, "issue_resolution"))
    resolution_note: str | None = Field(default=None, sa_type=sa.Text)
    resolved_by: UUID | None = Field(default=None, foreign_key="users.id")
    resolved_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class LessonReport(SQLModel):
    topic_covered: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    homework: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


class RecordingUploadIn(SQLModel):
    filename: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    content_type: str
    size: int = Field(gt=0)


class RecordingUpload(SQLModel):
    """Where the browser PUTs the file, with exactly this Content-Type header and size."""

    upload_url: str
    method: str = "PUT"
    content_type: str
    expires_at: datetime


class RecordingLink(SQLModel):
    url: str
    expires_at: datetime


class IssueCreate(SQLModel):
    kind: IssueKind
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]

    @model_validator(mode="after")
    def check_kind(self) -> "IssueCreate":
        if self.kind == IssueKind.no_report:
            raise ValueError("kind 'no_report' is raised automatically")
        return self


class IssueResolve(SQLModel):
    resolution: IssueResolution
    note: str | None = Field(default=None, max_length=2000)
    # Reschedule only: the new local date and time of the lesson.
    new_date: date | None = None
    new_start_time: time | None = None
    new_end_time: time | None = None

    @model_validator(mode="after")
    def check_reschedule(self) -> "IssueResolve":
        if self.resolution == IssueResolution.reschedule:
            if not (self.new_date and self.new_start_time and self.new_end_time):
                raise ValueError("reschedule needs new_date, new_start_time and new_end_time")
            if self.new_end_time <= self.new_start_time:
                raise ValueError("new_end_time must be after new_start_time")
        return self


class IssueRead(SQLModel):
    id: UUID
    lesson_id: UUID
    kind: IssueKind
    description: str | None
    raised_automatically: bool
    resolution: IssueResolution | None
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime


class LessonBase(SQLModel):
    id: UUID
    booking_id: UUID
    parent_id: UUID
    tutor_id: UUID
    lesson_date: date
    start_time: time
    end_time: time
    starts_at: datetime
    ends_at: datetime
    status: LessonStatus
    topic_covered: str | None
    homework: str | None
    reported_at: datetime | None
    problem_window_ends_at: datetime | None
    price: Decimal  # P: everyone sees it
    subjects: list[str] = []
    level: EducationLevel | None = None
    mode: LessonMode | None = None
    parent_name: str | None = None
    tutor_name: str | None = None
    issue: IssueRead | None = None
    recording_required: bool = False  # online lesson: the report needs a recording (spec 3 R2.1)
    has_recording: bool = False  # uploaded and not yet deleted: GET /lessons/{id}/recording gives a link


class LessonParentView(LessonBase):
    parent_price: Decimal


class LessonTutorView(LessonBase):
    tutor_earning: Decimal
    earning_status: EarningStatus
    payout_due_at: datetime


class LessonAdminView(LessonBase):
    parent_price: Decimal
    tutor_earning: Decimal
    earning_status: EarningStatus
    payout_due_at: datetime
    payout_id: UUID | None
