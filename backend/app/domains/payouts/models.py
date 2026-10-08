from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from pydantic import StringConstraints
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum
from app.domains.payments.models import TransferStatus, transfer_status_enum


class PayoutMethod(str, Enum):
    paystack = "paystack"  # sent by the app as a Paystack transfer
    manual = "manual"  # paid outside the app; the admin recorded it


# ---------- Tables ----------

class TutorBankAccount(BaseUUIDModel, table=True):
    """Where the tutor is paid. Only admins ever see the full account number (spec 1 R1.4)."""

    __tablename__ = "tutor_bank_accounts"

    tutor_id: UUID = Field(foreign_key="users.id", unique=True)
    bank_code: str
    bank_name: str
    account_number: str
    account_name: str  # as the bank reports it
    name_matches: bool  # account name matches the tutor's name
    override_note: str | None = Field(default=None, sa_type=sa.Text)  # admin accepted a mismatch
    overridden_by: UUID | None = Field(default=None, foreign_key="users.id")
    recipient_code: str | None = None  # Paystack transfer recipient, created on first payout


class Payout(BaseUUIDModel, table=True):
    """One payment to a tutor, covering one or more lesson earnings."""

    __tablename__ = "payouts"

    tutor_id: UUID = Field(foreign_key="users.id", index=True)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    lesson_count: int
    method: PayoutMethod = Field(sa_type=pg_enum(PayoutMethod, "payout_method"))
    status: TransferStatus = Field(sa_type=transfer_status_enum)
    reference: str = Field(unique=True)  # our transfer reference (PO-...)
    transfer_code: str | None = None
    note: str | None = Field(default=None, sa_type=sa.Text)
    created_by: UUID = Field(foreign_key="users.id")
    paid_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class BankAccountUpdate(SQLModel):
    bank_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=10)]
    account_number: Annotated[str, StringConstraints(pattern=r"^\d{10}$")]


class BankAccountTutorView(SQLModel):
    """The tutor's own view: bank name and last 4 digits only."""

    bank_name: str
    account_last4: str
    account_name: str
    name_matches: bool
    approved_for_payouts: bool


class BankAccountAdminView(SQLModel):
    bank_code: str
    bank_name: str
    account_number: str
    account_name: str
    name_matches: bool
    override_note: str | None


class BankOverride(SQLModel):
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]


class EarningsSummary(SQLModel):
    """The tutor's totals by earning status."""

    pending: Decimal
    on_hold: Decimal
    payable: Decimal
    paid: Decimal


class PayoutDue(SQLModel):
    """Admin payouts page: one row per tutor with payable earnings."""

    tutor_id: UUID
    tutor_name: str | None
    amount: Decimal
    lesson_count: int
    due_at: datetime  # earliest payout deadline among the payable earnings
    overdue: bool
    bank_account: BankAccountAdminView | None
    can_send: bool  # bank account present and name matches (or overridden)


class PayoutCreate(SQLModel):
    tutor_id: UUID
    method: PayoutMethod
    note: str | None = Field(default=None, max_length=1000)  # e.g. the bank transfer reference


class PayoutRead(SQLModel):
    id: UUID
    tutor_id: UUID
    tutor_name: str | None = None
    amount: Decimal
    lesson_count: int
    method: PayoutMethod
    status: TransferStatus
    reference: str
    note: str | None
    created_at: datetime
    paid_at: datetime | None


class PayoutReceiptLine(SQLModel):
    lesson_date: date
    subjects: list[str]
    parent_first_name: str
    price: Decimal  # agreed price (P)
    tutor_fee: Decimal  # P x T
    earning: Decimal  # what the tutor receives


class PayoutReceipt(SQLModel):
    """A tutor's receipt for one payout: the agreed price, TutorLink's fee and what they received,
    lesson by lesson. Never shows the parent's fee or total (spec 1 R1.2)."""

    receipt_number: str
    issued_at: datetime
    tutor_name: str | None
    tutor_email: str
    method: PayoutMethod
    status: TransferStatus
    tutor_fee_rate: Decimal | None  # None when lessons in the payout used different rates
    bank: str | None  # "Access Bank ****6789"
    lines: list[PayoutReceiptLine]
    total_price: Decimal
    total_fee: Decimal
    total: Decimal
