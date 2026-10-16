"""ID documents a tutor can start with before verifying their NIN (spec 11 R1)."""

from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum


class IdDocumentType(str, Enum):
    nin = "nin"  # NIN slip or card
    voters_card = "voters_card"
    drivers_licence = "drivers_licence"
    passport = "passport"  # international passport


ID_LABELS = {IdDocumentType.nin: "NIN slip", IdDocumentType.voters_card: "voter's card",
             IdDocumentType.drivers_licence: "driver's licence", IdDocumentType.passport: "international passport"}


class IdDocumentStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


# ---------- Tables ----------

class IdDocument(BaseUUIDModel, table=True):
    """Kept after the NIN is verified (R1.4). The file is private in storage (R1.1)."""

    __tablename__ = "id_documents"

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    type: IdDocumentType = Field(sa_type=pg_enum(IdDocumentType, "id_document_type"))
    file_key: str
    file_name: str
    status: IdDocumentStatus = Field(default=IdDocumentStatus.pending,
                                     sa_type=pg_enum(IdDocumentStatus, "id_document_status"))
    review_note: str | None = Field(default=None, sa_type=sa.Text)
    reviewed_by: UUID | None = Field(default=None, foreign_key="users.id")
    reviewed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class IdDocumentTutorView(SQLModel):
    id: UUID
    type: IdDocumentType
    file_name: str
    file_url: str  # short-lived (R1.1)
    status: IdDocumentStatus
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class IdDocumentAdminView(IdDocumentTutorView):
    """Next to the tutor's name, which the admin compares with the document (R1.2)."""

    tutor_id: UUID
    tutor_first_name: str
    tutor_middle_name: str | None
    tutor_surname: str


class IdReviewIn(SQLModel):
    status: IdDocumentStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check(self) -> "IdReviewIn":
        if self.status == IdDocumentStatus.pending:
            raise ValueError("status must be 'verified' or 'rejected'")
        self.note = (self.note or "").strip() or None
        if self.status == IdDocumentStatus.rejected and not self.note:
            raise ValueError("say why the ID document is rejected, so the tutor can fix it")
        return self
