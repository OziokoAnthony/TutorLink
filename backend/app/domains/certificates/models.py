"""Tutor certificates, uploaded by the tutor and checked by an admin (spec 4 R4)."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from pydantic import model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum


class CertificateType(str, Enum):
    """Certificate types a tutor can upload (R4.1); a job post can ask for one as a minimum (spec 2)."""

    waec = "WAEC"
    neco = "NECO"
    nabteb = "NABTEB"
    nce = "NCE"
    degree = "Degree"
    pgde = "PGDE"
    trcn = "TRCN"
    other = "Other"


# One PostgreSQL type, shared with job_posts.min_certificate.
certificate_type_enum = pg_enum(CertificateType, "certificate_type")


# Results the admin confirms on the exam body's own site with the tutor's checker PIN (R4.2).
CHECKER_TYPES = {CertificateType.waec, CertificateType.neco}


class CertificateStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


# ---------- Tables ----------

class Certificate(BaseUUIDModel, table=True):
    __tablename__ = "certificates"

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    type: CertificateType = Field(sa_type=certificate_type_enum)
    institution: str
    year: int = Field(sa_type=sa.SmallInteger)
    # The file, private in storage: only the tutor and admins get a link (R4.1).
    file_key: str
    file_name: str
    # WAEC/NECO only (R4.2). The PIN is encrypted and erased once the certificate is reviewed.
    exam_number: str | None = None
    exam_year: int | None = Field(default=None, sa_type=sa.SmallInteger)
    checker_pin_encrypted: str | None = None
    status: CertificateStatus = Field(
        default=CertificateStatus.pending,
        sa_type=pg_enum(CertificateStatus, "certificate_status"),
        sa_column_kwargs={"server_default": CertificateStatus.pending.value},
    )
    review_note: str | None = Field(default=None, sa_type=sa.Text)
    reviewed_by: UUID | None = Field(default=None, foreign_key="users.id")
    reviewed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class CertificateFields(SQLModel):
    """What the tutor tells us about a certificate, sent as form fields next to the file."""

    type: CertificateType
    institution: str = Field(min_length=2, max_length=200)
    year: int = Field(ge=1950)
    exam_number: str | None = Field(default=None, max_length=30)
    exam_year: int | None = Field(default=None, ge=1950)
    checker_pin: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def check(self) -> "CertificateFields":
        self.institution = " ".join(self.institution.split())
        this_year = date.today().year
        if self.year > this_year or (self.exam_year and self.exam_year > this_year):
            raise ValueError("the year can't be in the future")
        if self.type in CHECKER_TYPES:
            self.exam_number = (self.exam_number or "").strip() or None
            self.checker_pin = (self.checker_pin or "").strip() or None
            if not (self.exam_number and self.exam_year and self.checker_pin):
                raise ValueError("WAEC and NECO certificates need the exam number, exam year and result-checker PIN")
        else:
            self.exam_number = self.exam_year = self.checker_pin = None
        return self


class CertificateTutorView(SQLModel):
    """The tutor's own certificate. The checker PIN is never sent back, only whether one is held."""

    id: UUID
    type: CertificateType
    institution: str
    year: int
    file_name: str
    file_url: str
    exam_number: str | None
    exam_year: int | None
    has_checker_pin: bool
    status: CertificateStatus
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class CertificateAdminView(CertificateTutorView):
    """What the admin reviews (R4.3): the certificate next to the tutor's NIN-verified name, and the
    checker PIN while it's still held."""

    tutor_id: UUID
    tutor_first_name: str
    tutor_middle_name: str | None
    tutor_surname: str
    tutor_nin_verified: bool
    checker_pin: str | None


class ReviewRequest(SQLModel):
    status: CertificateStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def check(self) -> "ReviewRequest":
        if self.status == CertificateStatus.pending:
            raise ValueError("status must be 'verified' or 'rejected'")
        self.note = (self.note or "").strip() or None
        if self.status == CertificateStatus.rejected and not self.note:
            raise ValueError("say why the certificate is rejected, so the tutor can fix it")
        return self
