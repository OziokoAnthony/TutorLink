"""Parents' money: their own account number, the balance ledger, deposits and withdrawals.

The balance is never stored: it is the sum of the parent's wallet entries. Every change locks the
parent's user row first, so two requests can't spend the same money.
"""

import logging
import secrets
import time
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.core import paystack
from app.core.clock import money, to_kobo
from app.core.config import is_placeholder, settings
from app.db.base import utcnow
from app.domains.auth import service as auth_service
from app.domains.auth.models import ParentProfile, User, UserRole
from app.domains.bookings.models import BookingPeriod, PeriodStatus
from app.domains.notifications import service as notifications
from app.domains.payments.models import (
    BankRead,
    EntryKind,
    TransferStatus,
    VirtualAccount,
    VirtualAccountRead,
    WalletEntry,
    WalletEntryRead,
    WalletRead,
    Withdrawal,
    WithdrawalAdminRead,
    WithdrawalCreate,
    WithdrawalRead,
)

logger = logging.getLogger(__name__)


def paystack_configured() -> bool:
    return not is_placeholder(settings.PAYSTACK_SECRET_KEY)


# ---------- Ledger ----------

def lock_parent(session: Session, parent_id: UUID) -> None:
    """Serialises balance changes for one parent until the transaction ends."""
    session.exec(select(User.id).where(User.id == parent_id).with_for_update()).one()


def balance(session: Session, parent_id: UUID) -> Decimal:
    total = session.exec(
        select(func.coalesce(func.sum(WalletEntry.amount), 0)).where(WalletEntry.parent_id == parent_id)
    ).one()
    return money(Decimal(total))


def add_entry(session: Session, parent_id: UUID, kind: EntryKind, amount: Decimal, description: str,
              **links) -> WalletEntry:
    """Adds a ledger entry (positive adds to the balance). The caller holds the parent lock and commits."""
    entry = WalletEntry(parent_id=parent_id, kind=kind, amount=money(amount), description=description, **links)
    session.add(entry)
    session.flush()
    return entry


# ---------- Account number ----------

def get_virtual_account(session: Session, parent_id: UUID) -> VirtualAccount | None:
    return session.exec(select(VirtualAccount).where(VirtualAccount.parent_id == parent_id)).first()


def ensure_virtual_account(session: Session, parent_id: UUID) -> VirtualAccount | None:
    """The parent's own account number, created with Paystack the first time it's needed (spec 1 R3.1).
    Returns None (and logs) when Paystack isn't configured or refuses; the parent can retry later."""
    account = get_virtual_account(session, parent_id)
    if account is not None:
        return account
    if not paystack_configured():
        logger.info("Not creating an account number for parent %s: Paystack is not configured", parent_id)
        return None
    parent = session.get(User, parent_id)
    profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent_id)).first()
    names = (profile.full_name if profile else "TutorLink Parent").split()
    try:
        customer = paystack.create_customer(email=parent.email, first_name=names[0],
                                            last_name=names[-1] if len(names) > 1 else names[0],
                                            phone=profile.phone if profile else None)
        dedicated = paystack.create_dedicated_account(customer["customer_code"])
    except HTTPException:
        logger.warning("Could not create an account number for parent %s", parent_id)
        return None
    account = VirtualAccount(parent_id=parent_id, customer_code=customer["customer_code"],
                             account_number=dedicated["account_number"], account_name=dedicated["account_name"],
                             bank_name=dedicated["bank"]["name"])
    session.add(account)
    session.flush()
    return account


def request_virtual_account(session: Session, parent: User) -> VirtualAccountRead:
    if not paystack_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Payments are not set up yet")
    account = ensure_virtual_account(session, parent.id)
    if account is None:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Couldn't create your account number; please try again")
    session.commit()
    return VirtualAccountRead.model_validate(account)


def account_text(account: VirtualAccount | None) -> str:
    """For notifications: how to pay."""
    if account is None:
        return "Your TutorLink account number will appear on your dashboard shortly."
    return (f"Pay by bank transfer to {account.account_number} ({account.bank_name}, "
            f"{account.account_name}). It's your own TutorLink account number.")


# ---------- Wallet view ----------

def wallet(session: Session, parent: User) -> WalletRead:
    entries = session.exec(
        select(WalletEntry).where(WalletEntry.parent_id == parent.id)
        .order_by(WalletEntry.created_at.desc()).limit(100)
    ).all()
    due = session.exec(
        select(func.coalesce(func.sum(BookingPeriod.amount), 0))
        .where(BookingPeriod.parent_id == parent.id, BookingPeriod.status == PeriodStatus.due)
    ).one()
    account = get_virtual_account(session, parent.id)
    return WalletRead(
        balance=balance(session, parent.id),
        virtual_account=VirtualAccountRead.model_validate(account) if account else None,
        amount_due=money(Decimal(due)),
        entries=[WalletEntryRead.model_validate(e) for e in entries],
    )


# ---------- Deposits (from the Paystack webhook) ----------

def credit_deposit(session: Session, data: dict) -> UUID | None:
    """Credits a bank transfer into a parent's account number. Returns the parent's id, or None when the
    event isn't a deposit we can match or Paystack doesn't confirm it. Never credits a reference twice."""
    reference = data.get("reference")
    customer_code = (data.get("customer") or {}).get("customer_code")
    if not reference or not customer_code:
        return None
    account = session.exec(select(VirtualAccount).where(VirtualAccount.customer_code == customer_code)).first()
    if account is None:
        logger.warning("Deposit %s for unknown customer %s", reference, customer_code)
        return None
    # The signature only proves the sender knows our secret; ask Paystack itself that the money arrived.
    verified = paystack.verify_transaction(reference)
    amount_kobo = verified.get("amount")
    if (verified.get("status") != "success" or verified.get("reference") != reference
            or verified.get("currency") != "NGN" or not isinstance(amount_kobo, int) or amount_kobo <= 0
            or (verified.get("customer") or {}).get("customer_code") != customer_code):
        logger.warning("Deposit %s not confirmed by Paystack", reference)
        return None

    lock_parent(session, account.parent_id)
    if session.exec(select(WalletEntry.id).where(WalletEntry.reference == reference)).first():
        return None  # already credited
    amount = Decimal(amount_kobo) / 100
    add_entry(session, account.parent_id, EntryKind.deposit, amount, "Bank transfer received", reference=reference)
    notifications.notify(session, account.parent_id, "Payment received — thank you!",
                         f"We received {notifications.naira(amount)} into your TutorLink balance.",
                         "/dashboard/parent/wallet")
    return account.parent_id


# ---------- Banks ----------

_banks_cache: tuple[float, list[BankRead]] | None = None


def list_banks() -> list[BankRead]:
    global _banks_cache
    if _banks_cache is None or time.time() - _banks_cache[0] > 24 * 3600:
        banks = [BankRead(name=b["name"], code=b["code"]) for b in paystack.list_banks() if b.get("active", True)]
        _banks_cache = (time.time(), sorted(banks, key=lambda b: b.name))
    return _banks_cache[1]


def bank_name(code: str) -> str:
    for bank in list_banks():
        if bank.code == code:
            return bank.name
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown bank")


def admin_ids(session: Session) -> list[UUID]:
    return list(session.exec(select(User.id).where(User.role == UserRole.admin, User.is_active == True)).all())  # noqa: E712


def new_reference(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}-{secrets.token_hex(3)}"


# ---------- Withdrawals ----------

def _withdrawal_read(w: Withdrawal) -> WithdrawalRead:
    return WithdrawalRead.model_validate(w)


def request_withdrawal(session: Session, parent: User, data: WithdrawalCreate) -> WithdrawalRead:
    """Takes the amount from the balance now; the admin then sends it (spec 1 R3.6)."""
    name = bank_name(data.bank_code)
    resolved = paystack.resolve_account(data.account_number, data.bank_code)
    lock_parent(session, parent.id)
    if data.amount > balance(session, parent.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't withdraw more than your balance")
    withdrawal = Withdrawal(parent_id=parent.id, amount=money(data.amount), bank_code=data.bank_code, bank_name=name,
                            account_number=data.account_number, account_name=resolved["account_name"],
                            status=TransferStatus.pending, reference=new_reference("WD"))
    session.add(withdrawal)
    session.flush()
    add_entry(session, parent.id, EntryKind.withdrawal, -withdrawal.amount,
              f"Withdrawal to {name} {data.account_number[-4:].rjust(10, '*')}", withdrawal_id=withdrawal.id)
    for admin_id in admin_ids(session):
        notifications.notify(session, admin_id, "Withdrawal requested",
                             f"A parent asked to withdraw {notifications.naira(withdrawal.amount)}.",
                             "/admin/withdrawals", email=False)
    session.commit()
    session.refresh(withdrawal)
    return _withdrawal_read(withdrawal)


def my_withdrawals(session: Session, parent: User) -> list[WithdrawalRead]:
    rows = session.exec(select(Withdrawal).where(Withdrawal.parent_id == parent.id)
                        .order_by(Withdrawal.created_at.desc())).all()
    return [_withdrawal_read(w) for w in rows]


def admin_withdrawals(session: Session, status_: TransferStatus | None) -> list[WithdrawalAdminRead]:
    stmt = select(Withdrawal).order_by(Withdrawal.created_at.desc())
    if status_:
        stmt = stmt.where(Withdrawal.status == status_)
    return _admin_reads(session, list(session.exec(stmt).all()))


def _admin_reads(session: Session, rows: list[Withdrawal]) -> list[WithdrawalAdminRead]:
    names = auth_service.full_names(session, [w.parent_id for w in rows])
    return [WithdrawalAdminRead.model_validate(w, update={"parent_name": names.get(w.parent_id)}) for w in rows]


def _open_withdrawal(session: Session, withdrawal_id: UUID) -> Withdrawal:
    withdrawal = session.exec(select(Withdrawal).where(Withdrawal.id == withdrawal_id).with_for_update()).first()
    if withdrawal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Withdrawal not found")
    if withdrawal.status != TransferStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Withdrawal is already {withdrawal.status.value}")
    return withdrawal


def send_withdrawal(session: Session, admin: User, withdrawal_id: UUID) -> WithdrawalAdminRead:
    withdrawal = _open_withdrawal(session, withdrawal_id)
    recipient = paystack.create_transfer_recipient(name=withdrawal.account_name,
                                                   account_number=withdrawal.account_number,
                                                   bank_code=withdrawal.bank_code)
    transfer = paystack.initiate_transfer(amount_kobo=to_kobo(withdrawal.amount),
                                          recipient_code=recipient["recipient_code"],
                                          reference=withdrawal.reference, reason="TutorLink balance withdrawal")
    withdrawal.status = TransferStatus.processing
    withdrawal.transfer_code = transfer.get("transfer_code")
    withdrawal.processed_by = admin.id
    withdrawal.processed_at = utcnow()
    session.add(withdrawal)
    session.commit()
    return admin_withdrawals_one(session, withdrawal.id)


def mark_withdrawal_paid(session: Session, admin: User, withdrawal_id: UUID, note: str | None) -> WithdrawalAdminRead:
    withdrawal = _open_withdrawal(session, withdrawal_id)
    withdrawal.status = TransferStatus.paid
    withdrawal.note = note
    withdrawal.processed_by = admin.id
    withdrawal.processed_at = utcnow()
    session.add(withdrawal)
    notifications.notify(session, withdrawal.parent_id, "Withdrawal sent",
                         f"{notifications.naira(withdrawal.amount)} has been sent to your bank account.",
                         "/dashboard/parent/wallet")
    session.commit()
    return admin_withdrawals_one(session, withdrawal.id)


def reject_withdrawal(session: Session, admin: User, withdrawal_id: UUID, note: str | None) -> WithdrawalAdminRead:
    withdrawal = _open_withdrawal(session, withdrawal_id)
    lock_parent(session, withdrawal.parent_id)
    withdrawal.status = TransferStatus.rejected
    withdrawal.note = note
    withdrawal.processed_by = admin.id
    withdrawal.processed_at = utcnow()
    session.add(withdrawal)
    add_entry(session, withdrawal.parent_id, EntryKind.withdrawal_reversal, withdrawal.amount,
              "Withdrawal not sent: amount returned to your balance", withdrawal_id=withdrawal.id)
    notifications.notify(session, withdrawal.parent_id, "Withdrawal not sent",
                         f"Your withdrawal of {notifications.naira(withdrawal.amount)} was not sent and is "
                         f"back in your balance.{' Note: ' + note if note else ''}", "/dashboard/parent/wallet")
    session.commit()
    return admin_withdrawals_one(session, withdrawal.id)


def admin_withdrawals_one(session: Session, withdrawal_id: UUID) -> WithdrawalAdminRead:
    return _admin_reads(session, [session.get(Withdrawal, withdrawal_id)])[0]


def settle_withdrawal_transfer(session: Session, reference: str, succeeded: bool) -> None:
    """Outcome of a withdrawal's Paystack transfer (transfer.success / failed / reversed webhook)."""
    withdrawal = session.exec(select(Withdrawal).where(Withdrawal.reference == reference).with_for_update()).first()
    if withdrawal is None:
        return
    if succeeded and withdrawal.status == TransferStatus.processing:
        withdrawal.status = TransferStatus.paid
        notifications.notify(session, withdrawal.parent_id, "Withdrawal sent",
                             f"{notifications.naira(withdrawal.amount)} has been sent to your bank account.",
                             "/dashboard/parent/wallet")
    elif not succeeded and withdrawal.status in (TransferStatus.processing, TransferStatus.paid):
        lock_parent(session, withdrawal.parent_id)
        withdrawal.status = TransferStatus.failed
        add_entry(session, withdrawal.parent_id, EntryKind.withdrawal_reversal, withdrawal.amount,
                  "Withdrawal failed: amount returned to your balance", withdrawal_id=withdrawal.id)
        notifications.notify(session, withdrawal.parent_id, "Withdrawal failed",
                             f"Your withdrawal of {notifications.naira(withdrawal.amount)} failed and is back "
                             "in your balance.", "/dashboard/parent/wallet")
    session.add(withdrawal)
