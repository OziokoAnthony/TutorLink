from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum, utcnow


class InvoiceStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


# ---------- Tables ----------

class Invoice(BaseUUIDModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = (sa.UniqueConstraint("parent_id", "billing_month", "billing_year"),)

    parent_id: UUID = Field(foreign_key="users.id")
    billing_month: int = Field(sa_type=sa.SmallInteger)
    billing_year: int = Field(sa_type=sa.SmallInteger)
    total_sessions: int
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)
    commission_rate: Decimal = Field(max_digits=5, decimal_places=4)
    commission_amount: Decimal = Field(max_digits=10, decimal_places=2)
    total_amount: Decimal = Field(max_digits=10, decimal_places=2)
    paystack_reference: str | None = Field(default=None, index=True)
    status: InvoiceStatus = Field(
        default=InvoiceStatus.pending,
        sa_type=pg_enum(InvoiceStatus, "invoice_status"),
        sa_column_kwargs={"server_default": InvoiceStatus.pending.value},
    )
    paid_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


class InvoiceItem(SQLModel, table=True):
    """Spec defines no updated_at here, so this table doesn't use BaseUUIDModel."""

    __tablename__ = "invoice_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    invoice_id: UUID = Field(foreign_key="invoices.id", index=True)
    session_id: UUID = Field(foreign_key="sessions.id", unique=True)
    tutor_id: UUID = Field(foreign_key="users.id")
    session_date: date  # denormalized for display
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    commission_amount: Decimal = Field(max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=utcnow, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class GenerateInvoicesRequest(SQLModel):
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class InvoiceRead(SQLModel):
    id: UUID
    parent_id: UUID
    billing_month: int
    billing_year: int
    total_sessions: int
    subtotal: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    total_amount: Decimal
    paystack_reference: str | None
    status: InvoiceStatus
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvoiceItemRead(SQLModel):
    id: UUID
    session_id: UUID
    tutor_id: UUID
    session_date: date
    amount: Decimal
    commission_amount: Decimal


class InvoiceDetail(InvoiceRead):
    items: list[InvoiceItemRead] = []


class GenerateInvoicesResponse(SQLModel):
    created: int
    skipped_existing: int
    invoices: list[InvoiceRead]


class PaymentInitResponse(SQLModel):
    authorization_url: str
    reference: str
