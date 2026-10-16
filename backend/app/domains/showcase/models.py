"""What visitors see before signing up (spec 14): counts, price ranges and reviews, never a tutor (R1.1)."""

from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.domains.content.models import SubjectGroup
from app.domains.tutors.models import EducationLevel


class PublicStats(SQLModel):
    """R2.1, from the database."""

    verified_tutors: int
    lessons_taught: int
    average_rating: float | None
    rating_count: int


class PublicReview(SQLModel):
    """R3.1: the parent's first name, the stars and the comment, nothing else."""

    first_name: str
    rating: int
    comment: str
    created_at: datetime


class LevelPrices(SQLModel):
    """R4.2: per lesson, what a parent pays (TutorLink's fee included). None under 3 offers ("Prices vary")."""

    level: EducationLevel
    tutors: int
    min_price: Decimal | None
    max_price: Decimal | None


class PublicSubject(SQLModel):
    slug: str
    name: str
    group: SubjectGroup
    tutors: int


class PublicSubjectDetail(PublicSubject):
    levels: list[LevelPrices]
    reviews: list[PublicReview]


class LevelSubject(PublicSubject):
    min_price: Decimal | None
    max_price: Decimal | None


class PublicLevel(SQLModel):
    level: EducationLevel
    tutors: int
    subjects: list[LevelSubject]
