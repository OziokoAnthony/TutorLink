from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from pydantic import EmailStr, model_validator
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.reviews.models import TutorToRate
from app.domains.tutors.models import OfferIn, TutorProfileRead, clean_name_part


class UserRole(str, Enum):
    parent = "parent"
    tutor = "tutor"
    admin = "admin"


# ---------- Tables ----------

class User(BaseUUIDModel, table=True):
    __tablename__ = "users"

    email: str = Field(unique=True)  # personal email: notifications go here; parents and admins log in with it
    # Tutors only: the address TutorLink assigns them, e.g. o.anthony@tutorlink.com. Their only login.
    work_email: str | None = Field(default=None, unique=True)
    password_hash: str
    role: UserRole = Field(sa_type=pg_enum(UserRole, "user_role"))
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": sa.true()})
    photo_key: str | None = None  # profile picture in storage (spec 4 R1b)


class ParentProfile(BaseUUIDModel, table=True):
    __tablename__ = "parent_profiles"

    user_id: UUID = Field(foreign_key="users.id", unique=True)
    full_name: str
    phone: str | None = None
    address: str | None = Field(default=None, sa_type=sa.Text)


# ---------- DTOs ----------

class RegisterRequest(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt only uses the first 72 bytes
    role: UserRole
    full_name: str | None = Field(default=None, min_length=1, max_length=200)  # parents
    # Tutors give their names separately; full_name is built from them and their work email from both.
    first_name: str | None = Field(default=None, max_length=100)
    surname: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    # Parent-only
    address: str | None = None
    # Tutor-only (area and at least one offer are required for tutors)
    bio: str | None = None
    area: str | None = Field(default=None, max_length=120)
    offers: list[OfferIn] = Field(default=[], max_length=20)

    @model_validator(mode="after")
    def check_role_fields(self) -> "RegisterRequest":
        if self.role == UserRole.admin:
            raise ValueError("role must be 'parent' or 'tutor'")
        if self.role == UserRole.tutor:
            if not self.area or not self.offers:
                raise ValueError("tutors must provide area and at least one offer")
            self.first_name, self.surname = clean_name_part(self.first_name), clean_name_part(self.surname)
            if not self.first_name or not self.surname:
                raise ValueError("tutors must provide first_name and surname")
            self.full_name = f"{self.first_name} {self.surname}"
        elif not self.full_name or not self.full_name.strip():
            raise ValueError("full_name is required")
        return self


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(SQLModel):
    id: UUID
    email: str
    work_email: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
    photo_url: str | None = None


class ParentProfileRead(SQLModel):
    id: UUID
    user_id: UUID
    full_name: str
    phone: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime


class MeResponse(SQLModel):
    user: UserRead
    parent_profile: ParentProfileRead | None = None
    tutor_profile: TutorProfileRead | None = None
    # Parents only: tutors they've had a confirmed session with but haven't rated yet.
    tutors_to_rate: list[TutorToRate] = []
