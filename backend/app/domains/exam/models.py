"""The qualifying exam (spec 4 R5): a question bank written by Claude, and tutors' timed attempts."""

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import Field as PydanticField
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel
from app.domains.tutors.models import EducationLevel, education_level_enum

# A question's tag (R5.2): general reasoning, or one subject at one level. General questions have
# subject_key "" and no level; subject_key is the subject in lower case, so offers match it in any case.
GENERAL_KEY = ""


# ---------- Tables ----------

class ExamQuestion(BaseUUIDModel, table=True):
    """One bank question. Its key and explanation never reach a tutor (R5.5)."""

    __tablename__ = "exam_questions"
    __table_args__ = (sa.Index("ix_exam_questions_tag", "subject_key", "level"),)

    subject_key: str = GENERAL_KEY
    subject: str | None = None  # as tutors write it, for admins
    level: EducationLevel | None = Field(default=None, sa_type=education_level_enum)
    text: str = Field(sa_type=sa.Text)
    options: list[str] = Field(sa_type=ARRAY(sa.String))  # four, in the order shown
    correct_index: int = Field(sa_type=sa.SmallInteger)
    explanation: str = Field(sa_type=sa.Text)
    text_hash: str = Field(unique=True)  # the same question is never stored twice
    model: str  # the Claude model that wrote it
    retired_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))  # never served again


class ExamAttempt(BaseUUIDModel, table=True):
    __tablename__ = "exam_attempts"

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    started_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    deadline: datetime = Field(sa_type=sa.DateTime(timezone=True))  # started_at + 30 minutes (R5.4)
    submitted_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    score: int | None = None
    total: int = 20
    passed: bool | None = None


class ExamAttemptQuestion(SQLModel, table=True):
    __tablename__ = "exam_attempt_questions"
    __table_args__ = (sa.UniqueConstraint("attempt_id", "position"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    attempt_id: UUID = Field(foreign_key="exam_attempts.id", index=True)
    question_id: UUID = Field(foreign_key="exam_questions.id", index=True)
    position: int = Field(sa_type=sa.SmallInteger)  # 1-20
    chosen_index: int | None = Field(default=None, sa_type=sa.SmallInteger)  # saved before the deadline only


# ---------- DTOs (tutor) ----------

class AttemptQuestionView(SQLModel):
    """A question as the tutor sees it: no correct answer, no explanation (R5.5)."""

    position: int
    text: str
    options: list[str]
    chosen_index: int | None


class AttemptView(SQLModel):
    id: UUID
    started_at: datetime
    deadline: datetime
    questions: list[AttemptQuestionView]


class AttemptResult(SQLModel):
    """After submitting: only the score and pass/fail, never which answers were right (R5.5)."""

    id: UUID
    started_at: datetime
    submitted_at: datetime
    score: int
    total: int
    passed: bool
    seconds_taken: int


class ExamStatus(SQLModel):
    passed: bool
    open_attempt: AttemptView | None
    attempts_left: int  # before the 24-hour lock (R5.7)
    locked_until: datetime | None
    attempts: list[AttemptResult]  # newest first
    pass_mark: int
    total: int
    minutes: int


class AnswerIn(SQLModel):
    position: int = PydanticField(ge=1, le=20)
    choice: int = PydanticField(ge=0, le=3)


class AnswersIn(SQLModel):
    answers: list[AnswerIn] = PydanticField(min_length=1, max_length=20)


# ---------- DTOs (admin) ----------

class AdminAttempt(AttemptResult):
    tutor_id: UUID
    tutor_name: str


class AdminQuestion(SQLModel):
    id: UUID
    subject: str | None
    level: EducationLevel | None
    text: str
    options: list[str]
    correct_index: int
    explanation: str
    model: str
    retired_at: datetime | None
    created_at: datetime


class BankLevel(SQLModel):
    """How full the bank is for one tag (R5.2): active questions against the target."""

    subject: str | None  # None for general reasoning
    level: EducationLevel | None
    active: int
    target: int
