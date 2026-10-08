from datetime import datetime
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import utcnow


# ---------- Tables ----------

class PlatformFees(SQLModel, table=True):
    """Single row (id=1): the current fee rates. Bookings copy them when accepted (spec 1 R1.1)."""

    __tablename__ = "platform_fees"
    __table_args__ = (sa.CheckConstraint("id = 1", name="single_row"),)

    id: int = Field(default=1, primary_key=True)
    parent_fee_rate: Decimal = Field(max_digits=5, decimal_places=4)  # S, added on top of the agreed price
    tutor_fee_rate: Decimal = Field(max_digits=5, decimal_places=4)  # T, taken from the agreed price
    updated_by: UUID | None = Field(default=None, foreign_key="users.id")
    updated_at: datetime = Field(default_factory=utcnow, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class FeesUpdate(SQLModel):
    parent_fee_rate: Decimal = Field(ge=0, le=Decimal("0.5"), max_digits=5, decimal_places=4)
    tutor_fee_rate: Decimal = Field(ge=0, le=Decimal("0.5"), max_digits=5, decimal_places=4)


class FeesRead(SQLModel):
    parent_fee_rate: Decimal
    tutor_fee_rate: Decimal
    updated_at: datetime
