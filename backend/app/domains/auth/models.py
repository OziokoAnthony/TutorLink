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
    password_hash: str | None = None  # None for a parent who signed up with Google and hasn't set one (R1.4)
    role: UserRole = Field(sa_type=pg_enum(UserRole, "user_role"))
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": sa.true()})
    photo_key: str | None = None  # profile picture in storage (spec 4 R1b)


class ParentProfile(BaseUUIDModel, table=True):
    __tablename__ = "parent_profiles"

    user_id: UUID = Field(foreign_key="users.id", unique=True)
    full_name: str
    phone: str | None = None
    address: str | None = Field(default=None, sa_type=sa.Text)


class PasswordResetToken(BaseUUIDModel, table=True):
    """A "Forgot password?" link (spec 4 R0.7). Only a hash of the token is stored; it works once."""

    __tablename__ = "password_reset_tokens"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True)
    expires_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
    used_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class ProfileFields(SQLModel):
    """What a new parent or tutor tells us about themselves, however they sign up."""

    role: UserRole
    full_name: str | None = Field(default=None, min_length=1, max_length=200)  # parents
    # Tutors give their names separately, exactly as on their NIN record (spec 4 R3.1); full_name is built
    # from first name and surname, and so is their work email.
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)  # only if the NIN record has one
    surname: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    # Parent-only
    address: str | None = None
    # Tutor-only (area and at least one offer are required for tutors)
    bio: str | None = None
    area: str | None = Field(default=None, max_length=120)
    offers: list[OfferIn] = Field(default=[], max_length=20)

    def check_profile(self) -> None:
        if self.role == UserRole.admin:
            raise ValueError("role must be 'parent' or 'tutor'")
        if self.role == UserRole.tutor:
            if not self.area or not self.offers:
                raise ValueError("tutors must provide area and at least one offer")
            self.first_name, self.surname = clean_name_part(self.first_name), clean_name_part(self.surname)
            self.middle_name = clean_name_part(self.middle_name) or None
            if not self.first_name or not self.surname:
                raise ValueError("tutors must provide first_name and surname")
            self.full_name = f"{self.first_name} {self.surname}"
        elif not self.full_name or not self.full_name.strip():
            raise ValueError("full_name is required")


class RegisterRequest(ProfileFields):
    """Email and password sign-up: parents only. Tutors register with Google (spec 4 R1.1)."""

    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=72)  # bcrypt only uses the first 72 bytes

    @model_validator(mode="after")
    def check_role_fields(self) -> "RegisterRequest":
        if self.role == UserRole.tutor:
            raise ValueError("tutors register with Google")
        self.check_profile()
        if self.password is None:
            raise ValueError("password is required")
        return self


class GoogleRegisterRequest(ProfileFields):
    """Sign-up with Google: tutors always, parents optionally (spec 4 R1.1, R1.4). The email is the
    verified one in the Google ID token; tutors are given a password, parents have none until they set one."""

    id_token: str
    use_google_photo: bool = False  # start with the Google account photo (R1b.3)

    @model_validator(mode="after")
    def check_role_fields(self) -> "GoogleRegisterRequest":
        self.check_profile()
        return self


class GoogleLoginRequest(SQLModel):
    id_token: str


class ForgotPasswordRequest(SQLModel):
    email: EmailStr


class ResetPasswordRequest(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(SQLModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


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


class GoogleRegisterResponse(MeResponse):
    """Tutors get their generated password, shown once (R1.2) and log in with it; parents are signed in."""

    password: str | None = None
    access_token: str | None = None
