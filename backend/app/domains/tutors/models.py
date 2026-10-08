from datetime import datetime, time
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import StringConstraints, model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.certificates.models import CertificateType
from app.domains.onboarding.models import NinCheckRead


class VettingStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EducationLevel(str, Enum):
    primary = "primary"
    junior_secondary = "junior_secondary"
    senior_secondary = "senior_secondary"


# Shared by tutor_offers.level and bookings.level (one PostgreSQL type).
education_level_enum = pg_enum(EducationLevel, "education_level")


# ---------- Tables ----------

class TutorProfile(BaseUUIDModel, table=True):
    __tablename__ = "tutor_profiles"

    user_id: UUID = Field(foreign_key="users.id", unique=True)
    # Exactly as on the tutor's NIN record (spec 4 R3.1); locked once the NIN is verified (R3.5).
    first_name: str
    middle_name: str | None = None
    surname: str
    full_name: str  # "first_name surname", kept for display everywhere
    phone: str | None = None
    bio: str | None = Field(default=None, sa_type=sa.Text)
    area: str
    vetting_status: VettingStatus = Field(
        default=VettingStatus.pending,
        sa_type=pg_enum(VettingStatus, "vetting_status"),
        sa_column_kwargs={"server_default": VettingStatus.pending.value},
    )
    vetting_note: str | None = Field(default=None, sa_type=sa.Text)
    vetted_by: UUID | None = Field(default=None, foreign_key="users.id")
    vetted_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    nin_verified_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))  # spec 4 R3.4


class TutorOffer(BaseUUIDModel, table=True):
    """Something a tutor teaches: one or more subjects at one level, when, and one price per lesson
    (spec 1 R0). Removing an offer only deactivates it, since bookings may point at it."""

    __tablename__ = "tutor_offers"

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    level: EducationLevel = Field(sa_type=education_level_enum)
    price: Decimal = Field(max_digits=10, decimal_places=2)
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": sa.true()})


class TutorOfferSubject(SQLModel, table=True):
    __tablename__ = "tutor_offer_subjects"
    __table_args__ = (sa.UniqueConstraint("offer_id", "subject"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    offer_id: UUID = Field(foreign_key="tutor_offers.id")
    subject: str


class TutorOfferWindow(SQLModel, table=True):
    """A weekly time the tutor can teach this offer."""

    __tablename__ = "tutor_offer_windows"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    offer_id: UUID = Field(foreign_key="tutor_offers.id", index=True)
    day_of_week: int = Field(sa_type=sa.SmallInteger)  # 0=Monday ... 6=Sunday
    start_time: time
    end_time: time


# ---------- DTOs ----------

class WeeklyTime(SQLModel):
    """A weekly time range, used for offer windows and booking slots."""

    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def check_times(self) -> "WeeklyTime":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


def clean_subjects(subjects: list[str]) -> list[str]:
    """Trimmed, de-duplicated (case-insensitively), in the order given."""
    seen, cleaned = set(), []
    for subject in subjects:
        name = subject.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            cleaned.append(name)
    if not cleaned:
        raise ValueError("at least one subject is required")
    return cleaned


class OfferIn(SQLModel):
    subjects: list[Annotated[str, StringConstraints(max_length=100)]] = Field(min_length=1, max_length=10)
    level: EducationLevel
    windows: list[WeeklyTime] = Field(min_length=1, max_length=21)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def clean(self) -> "OfferIn":
        self.subjects = clean_subjects(self.subjects)
        return self


class OfferRead(SQLModel):
    id: UUID
    subjects: list[str]
    level: EducationLevel
    windows: list[WeeklyTime]
    price: Decimal


def clean_name_part(value: str | None) -> str:
    """Trims a name and collapses inner spaces: "  Anthony   Chidi " -> "Anthony Chidi"."""
    return " ".join((value or "").split())


NamePart = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class TutorName(SQLModel):
    """A tutor's name exactly as on their NIN record (spec 4 R3.1)."""

    first_name: NamePart
    middle_name: str | None = Field(default=None, max_length=100)  # only if the NIN record has one
    surname: NamePart

    @model_validator(mode="after")
    def clean_names(self) -> "TutorName":
        self.first_name, self.surname = clean_name_part(self.first_name), clean_name_part(self.surname)
        self.middle_name = clean_name_part(self.middle_name) or None
        return self


class TutorProfileUpsert(TutorName):
    phone: str | None = Field(default=None, max_length=30)
    bio: str | None = None
    area: str = Field(min_length=1, max_length=120)


class TutorProfileRead(SQLModel):
    """Full profile, for the tutor themself and admins."""

    id: UUID
    user_id: UUID
    first_name: str
    middle_name: str | None
    surname: str
    full_name: str
    phone: str | None
    bio: str | None
    area: str
    vetting_status: VettingStatus
    vetting_note: str | None
    vetted_at: datetime | None
    nin_verified_at: datetime | None
    nin_check: NinCheckRead | None = None  # the latest NIN attempt (R3.9)
    created_at: datetime
    updated_at: datetime
    photo_url: str | None = None
    offers: list[OfferRead] = []
    price_from: Decimal | None = None  # lowest offer price
    average_rating: Decimal | None = None  # 1.00-5.00, None until first rating
    rating_count: int = 0


class TutorPublic(SQLModel):
    """Public listing shape: no contact or vetting details, only the badges (spec 4 R4.4)."""

    id: UUID
    user_id: UUID
    full_name: str
    bio: str | None
    area: str
    photo_url: str | None = None
    nin_verified: bool = False
    verified_certificates: list[CertificateType] = []  # types only: no files or numbers
    offers: list[OfferRead] = []
    price_from: Decimal | None = None
    average_rating: Decimal | None = None  # 1.00-5.00, None until first rating
    rating_count: int = 0


class VetRequest(SQLModel):
    status: Literal["approved", "rejected"]
    note: str | None = None
