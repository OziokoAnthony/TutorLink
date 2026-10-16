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


class LegalAudience(str, Enum):
    """Parents and tutors each have their own three documents (spec 9 R1)."""

    parent = "parent"
    tutor = "tutor"


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
    """One published version of the parents' or tutors' privacy notice, terms or disclaimer (spec 7 R2, spec 9
    R1). The latest of each audience and kind is shown and must be agreed to."""

    __tablename__ = "legal_documents"
    __table_args__ = (sa.Index("ix_legal_documents_audience_kind_created_at", "audience", "kind", "created_at"),)

    audience: LegalAudience = Field(sa_type=pg_enum(LegalAudience, "legal_audience"))
    kind: LegalKind = Field(sa_type=pg_enum(LegalKind, "legal_kind"))
    body: str = Field(sa_type=sa.Text)
    published_by: UUID | None = Field(default=None, foreign_key="users.id")


class LegalAcceptance(BaseUUIDModel, table=True):
    """Proof that a parent or tutor agreed to one version of one document (spec 9 R2.2). Never edited or deleted."""

    __tablename__ = "legal_acceptances"
    __table_args__ = (sa.UniqueConstraint("user_id", "document_id", name="uq_legal_acceptances_user_document"),)

    user_id: UUID = Field(foreign_key="users.id", index=True)
    document_id: UUID = Field(foreign_key="legal_documents.id")
    ip: str | None = Field(default=None, max_length=64)


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
    audience: LegalAudience
    kind: LegalKind
    body: str
    published_at: datetime


class MyLegalDocument(LegalRead):
    id: UUID  # the version, sent back when agreeing
    accepted_at: datetime | None  # when this reader agreed to this version


class MyLegal(SQLModel):
    """A parent's or tutor's own three documents (spec 9 R2.4)."""

    required: bool  # they can't continue until they agree (R3, R5)
    can_accept: bool  # False for a tutor who hasn't finished the other onboarding steps (R4.1)
    documents: list[MyLegalDocument]


class AcceptLegalIn(SQLModel):
    document_ids: list[UUID]  # the latest version of each of the reader's three documents (R2.1, R2.3)


class LegalVersion(LegalRead):
    id: UUID
    published_by: str | None  # the admin's email
