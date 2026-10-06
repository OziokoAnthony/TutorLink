from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel


# ---------- Tables ----------

class TutorReview(BaseUUIDModel, table=True):
    """One review per (parent, tutor). The parent can update it; it never duplicates."""

    __tablename__ = "tutor_reviews"
    __table_args__ = (
        sa.UniqueConstraint("tutor_id", "parent_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    tutor_id: UUID = Field(foreign_key="users.id")  # covered by the unique constraint's index
    parent_id: UUID = Field(foreign_key="users.id", index=True)
    rating: int = Field(sa_type=sa.SmallInteger)  # 1-5 stars
    comment: str | None = Field(default=None, sa_type=sa.Text)


# ---------- DTOs ----------

class ReviewUpsert(SQLModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewRead(SQLModel):
    """The parent's own review."""

    id: UUID
    tutor_id: UUID
    rating: int
    comment: str | None
    created_at: datetime
    updated_at: datetime


class PublicReview(SQLModel):
    """What other parents see: no parent id or email, first name only."""

    rating: int
    comment: str | None
    parent_first_name: str
    created_at: datetime
    updated_at: datetime


class TutorToRate(SQLModel):
    tutor_id: UUID
    full_name: str
