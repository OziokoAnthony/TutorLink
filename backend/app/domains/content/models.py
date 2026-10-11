import re
from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum


class SubjectGroup(str, Enum):
    nigerian = "nigerian"
    international = "international"


class LegalKind(str, Enum):
    privacy = "privacy"
    terms = "terms"
    disclaimer = "disclaimer"


# ---------- Tables ----------

class Subject(BaseUUIDModel, table=True):
    """A subject tutors can offer and parents can post jobs for (spec 7 R1). `key` is the name in lower case with
    single spaces, so "further  MATHEMATICS" and "Further Mathematics" are the same subject."""

    __tablename__ = "subjects"

    name: str = Field(max_length=60)
    key: str = Field(max_length=60, sa_column_kwargs={"unique": True})
    group: SubjectGroup = Field(sa_type=pg_enum(SubjectGroup, "subject_group"))
    # False once an admin removes it: hidden from new offers and jobs; existing ones keep it (R1.4).
    is_offered: bool = Field(default=True)


class LegalDocument(BaseUUIDModel, table=True):
    """One published version of the privacy notice, terms or disclaimer (spec 7 R2). The latest is shown."""

    __tablename__ = "legal_documents"

    kind: LegalKind = Field(sa_type=pg_enum(LegalKind, "legal_kind"), index=True)
    body: str = Field(sa_type=sa.Text)
    published_by: UUID | None = Field(default=None, foreign_key="users.id")


# ---------- DTOs ----------

SUBJECT_NAME = re.compile(r"^[A-Za-z0-9&()\-'.,/ ]+$")


def subject_key(name: str) -> str:
    return " ".join(name.lower().split())


class SubjectRead(SQLModel):
    name: str
    group: SubjectGroup


class SubjectAdminView(SQLModel):
    id: UUID
    name: str
    group: SubjectGroup
    is_offered: bool
    offers: int  # active tutor offers that teach it


class SubjectIn(SQLModel):
    name: str
    group: SubjectGroup

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        """R1.3. The name reaches Claude's exam prompt, so it's kept to plain characters."""
        v = " ".join(v.split())
        if not 2 <= len(v) <= 60:
            raise ValueError("A subject name is 2 to 60 characters")
        if not SUBJECT_NAME.match(v):
            raise ValueError("A subject name can only use letters, numbers, spaces and & ( ) - ' . , /")
        return v


class SubjectOfferedIn(SQLModel):
    is_offered: bool


class LegalIn(SQLModel):
    body: str = Field(min_length=100, max_length=50_000)  # R2.5
    notify: bool = False  # R2.4


class LegalRead(SQLModel):
    kind: LegalKind
    body: str
    published_at: datetime


class LegalVersion(LegalRead):
    id: UUID
    published_by: str | None  # the admin's email
