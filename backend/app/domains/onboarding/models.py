"""Tutor onboarding (spec 4 R2) and NIN verification (R3)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel


# ---------- Tables ----------

class NinVerification(BaseUUIDModel, table=True):
    """One NIN check with Dojah. Never stores the full NIN, the NIN record's name or photo, or the
    selfie (R3.7): only the last 4 digits, a keyed hash (one NIN verifies one account, R3.6) and the
    result of each check (R3.3)."""

    __tablename__ = "nin_verifications"
    __table_args__ = (
        sa.Index("uq_nin_verifications_verified_nin_hash", "nin_hash", unique=True,
                 postgresql_where=sa.text("verified")),
    )

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    nin_last4: str
    nin_hash: str = Field(index=True)
    nin_found: bool
    name_matches: bool | None = None  # None when the NIN wasn't found
    selfie_matches: bool | None = None
    verified: bool
    dojah_reference: str | None = None
    checked_at: datetime = Field(sa_type=sa.DateTime(timezone=True))  # clock.now(): attempts are limited by it (R3.8)


# ---------- DTOs ----------

class NinCheckRead(SQLModel):
    """What the tutor and admins see of a NIN check (R3.4, R3.9): no name from the NIN record."""

    verified: bool
    nin_last4: str
    nin_found: bool
    name_matches: bool | None
    selfie_matches: bool | None
    checked_at: datetime


class NinResult(NinCheckRead):
    message: str  # which check failed, or that the NIN is verified
    attempts_left: int  # in the current 24 hours


StepKey = Literal["profile", "nin", "certificates", "review"]


class OnboardingStep(SQLModel):
    key: StepKey
    done: bool
    todo: list[str] = []  # what's still missing, in words the tutor can act on


class Onboarding(SQLModel):
    """The tutor's checklist (R2.1), in order. The quiz (R5) joins it when built."""

    steps: list[OnboardingStep]
    vetting_status: str
    nin_attempts_left: int
    nin_retry_at: datetime | None = None  # when the next NIN attempt is allowed, if none are left
