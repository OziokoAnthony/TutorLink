from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated
from uuid import UUID, uuid4

import sqlalchemy as sa
from pydantic import StringConstraints
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum, utcnow


class EntryKind(str, Enum):
    deposit = "deposit"  # bank transfer into the parent's account number (+)
    period_payment = "period_payment"  # a billing period paid from the balance (-)
    refund = "refund"  # money back to the balance (+)
    withdrawal = "withdrawal"  # money sent back to the parent's bank (-)
    withdrawal_reversal = "withdrawal_reversal"  # a withdrawal that failed or was rejected (+)


class RefundReason(str, Enum):
    cancellation = "cancellation"
    lesson_issue = "lesson_issue"


class RefundStatus(str, Enum):
    pending = "pending"  # waiting for the admin (cancellations)
    approved = "approved"
    rejected = "rejected"


class TransferStatus(str, Enum):
    """Shared by withdrawals and tutor payouts."""

    pending = "pending"  # waiting for the admin (withdrawals only)
    processing = "processing"  # sent to Paystack, outcome not known yet
    paid = "paid"
    failed = "failed"
    rejected = "rejected"  # withdrawal turned down by the admin


transfer_status_enum = pg_enum(TransferStatus, "transfer_status")


# ---------- Tables ----------

class VirtualAccount(BaseUUIDModel, table=True):
    """The parent's own Paystack account number. Transfers into it land in the platform balance."""

    __tablename__ = "virtual_accounts"

    parent_id: UUID = Field(foreign_key="users.id", unique=True)
    customer_code: str = Field(unique=True)
    account_number: str
    account_name: str
    bank_name: str


class WalletEntry(SQLModel, table=True):
    """The parent's balance ledger. The balance is always the sum of a parent's entries."""

    __tablename__ = "wallet_entries"
    __table_args__ = (sa.Index("ix_wallet_entries_parent_id_created_at", "parent_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    parent_id: UUID = Field(foreign_key="users.id")
    kind: EntryKind = Field(sa_type=pg_enum(EntryKind, "wallet_entry_kind"))
    amount: Decimal = Field(max_digits=12, decimal_places=2)  # + adds to the balance, - takes from it
    description: str
    # A deposit's Paystack reference, so the same transfer is never credited twice.
    reference: str | None = Field(default=None, unique=True)
    period_id: UUID | None = Field(default=None, foreign_key="booking_periods.id")
    refund_id: UUID | None = Field(default=None, foreign_key="refunds.id")
    withdrawal_id: UUID | None = Field(default=None, foreign_key="withdrawals.id")
    created_at: datetime = Field(default_factory=utcnow, sa_type=sa.DateTime(timezone=True))


class Refund(BaseUUIDModel, table=True):
    __tablename__ = "refunds"

    parent_id: UUID = Field(foreign_key="users.id", index=True)
    booking_id: UUID = Field(foreign_key="bookings.id")
    reason: RefundReason = Field(sa_type=pg_enum(RefundReason, "refund_reason"))
    lesson_count: int
    amount: Decimal = Field(max_digits=12, decimal_places=2)  # agreed price only, parent fee excluded
    status: RefundStatus = Field(sa_type=pg_enum(RefundStatus, "refund_status"))
    note: str | None = Field(default=None, sa_type=sa.Text)
    decided_by: UUID | None = Field(default=None, foreign_key="users.id")
    decided_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


class Withdrawal(BaseUUIDModel, table=True):
    """The parent asked for balance to be sent back to their bank. The admin sends it."""

    __tablename__ = "withdrawals"

    parent_id: UUID = Field(foreign_key="users.id", index=True)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    bank_code: str
    bank_name: str
    account_number: str
    account_name: str
    status: TransferStatus = Field(sa_type=transfer_status_enum)
    reference: str = Field(unique=True)  # our transfer reference (WD-...)
    transfer_code: str | None = None
    note: str | None = Field(default=None, sa_type=sa.Text)
    processed_by: UUID | None = Field(default=None, foreign_key="users.id")
    processed_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class VirtualAccountRead(SQLModel):
    account_number: str
    account_name: str
    bank_name: str


class WalletEntryRead(SQLModel):
    id: UUID
    kind: EntryKind
    amount: Decimal
    description: str
    created_at: datetime


class WalletRead(SQLModel):
    balance: Decimal
    virtual_account: VirtualAccountRead | None
    amount_due: Decimal  # total of billing periods waiting to be paid
    entries: list[WalletEntryRead]


class WithdrawalCreate(SQLModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    bank_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=10)]
    account_number: Annotated[str, StringConstraints(pattern=r"^\d{10}$")]


class WithdrawalRead(SQLModel):
    id: UUID
    amount: Decimal
    bank_name: str
    account_number: str
    account_name: str
    status: TransferStatus
    note: str | None
    created_at: datetime
    processed_at: datetime | None


class WithdrawalAdminRead(WithdrawalRead):
    parent_id: UUID
    parent_name: str | None = None
    bank_code: str
    reference: str


class RefundRead(SQLModel):
    id: UUID
    parent_id: UUID
    booking_id: UUID
    reason: RefundReason
    lesson_count: int
    amount: Decimal
    status: RefundStatus
    note: str | None
    decided_at: datetime | None
    created_at: datetime
    parent_name: str | None = None


class AdminDecision(SQLModel):
    note: str | None = Field(default=None, max_length=1000)


class BankRead(SQLModel):
    name: str
    code: str
