"""Paying tutors (spec 1 R6): bank details, what each tutor is owed, and payouts by the admin."""

import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.core import clock
from app.core import paystack
from app.core.clock import money, to_kobo
from app.domains.auth import service as auth_service
from app.domains.auth.models import User, UserRole
from app.domains.bookings.models import Booking
from app.domains.lessons.models import EarningStatus, Lesson
from app.domains.notifications import service as notifications
from app.domains.payments import service as payments
from app.domains.payments.models import TransferStatus
from app.domains.payouts.models import (
    BankAccountAdminView,
    BankAccountTutorView,
    BankAccountUpdate,
    EarningsSummary,
    Payout,
    PayoutCreate,
    PayoutDue,
    PayoutMethod,
    PayoutRead,
    PayoutReceipt,
    PayoutReceiptLine,
    TutorBankAccount,
)
from app.domains.tutors import service as tutor_service


def _words(name: str) -> set[str]:
    return set(re.findall(r"[a-z]+", name.lower()))


def names_match(tutor_name: str, account_name: str) -> bool:
    """Every part of the tutor's name appears in the bank account name, in any order
    (banks often write "SURNAME FIRSTNAME MIDDLE")."""
    wanted = _words(tutor_name)
    return bool(wanted) and wanted <= _words(account_name)


# ---------- Bank details ----------

def _bank(session: Session, tutor_id: UUID) -> TutorBankAccount | None:
    return session.exec(select(TutorBankAccount).where(TutorBankAccount.tutor_id == tutor_id)).first()


def _cleared(account: TutorBankAccount | None) -> bool:
    return account is not None and (account.name_matches or account.override_note is not None)


def _tutor_view(account: TutorBankAccount) -> BankAccountTutorView:
    return BankAccountTutorView(bank_name=account.bank_name, account_last4=account.account_number[-4:],
                                account_name=account.account_name, name_matches=account.name_matches,
                                approved_for_payouts=_cleared(account))


def get_my_bank_account(session: Session, tutor: User) -> BankAccountTutorView | None:
    account = _bank(session, tutor.id)
    return _tutor_view(account) if account else None


def set_bank_account(session: Session, tutor: User, data: BankAccountUpdate) -> BankAccountTutorView:
    profile = tutor_service.get_profile_by_user_id(session, tutor.id)
    bank_name = payments.bank_name(data.bank_code)
    resolved = paystack.resolve_account(data.account_number, data.bank_code)
    account = _bank(session, tutor.id) or TutorBankAccount(tutor_id=tutor.id, bank_code="", bank_name="",
                                                           account_number="", account_name="", name_matches=False)
    account.bank_code = data.bank_code
    account.bank_name = bank_name
    account.account_number = data.account_number
    account.account_name = resolved["account_name"]
    account.name_matches = names_match(profile.full_name if profile else "", resolved["account_name"])
    account.override_note = account.overridden_by = account.recipient_code = None
    session.add(account)
    if not account.name_matches:
        for admin_id in payments.admin_ids(session):
            notifications.notify(session, admin_id, "Tutor bank name doesn't match",
                                 "A tutor's bank account name doesn't match their profile. Review it on the payouts page.",
                                 "/admin/payouts", email=False)
    session.commit()
    return _tutor_view(account)


def override_bank_account(session: Session, admin: User, tutor_id: UUID, note: str) -> BankAccountAdminView:
    account = _bank(session, tutor_id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This tutor hasn't added bank details")
    account.override_note = note
    account.overridden_by = admin.id
    session.add(account)
    session.commit()
    return BankAccountAdminView.model_validate(account)


# ---------- Earnings ----------

def earnings_summary(session: Session, tutor: User) -> EarningsSummary:
    rows = session.exec(select(Lesson.earning_status, func.coalesce(func.sum(Lesson.tutor_earning), 0))
                        .where(Lesson.tutor_id == tutor.id).group_by(Lesson.earning_status)).all()
    totals = {s: Decimal(0) for s in EarningStatus}
    for earning_status, total in rows:
        totals[earning_status] = money(Decimal(total))
    return EarningsSummary(pending=totals[EarningStatus.pending], on_hold=totals[EarningStatus.on_hold],
                           payable=totals[EarningStatus.payable], paid=totals[EarningStatus.paid])


def payouts_due(session: Session, now: datetime | None = None) -> list[PayoutDue]:
    now = now or clock.now()
    rows = session.exec(select(Lesson).where(Lesson.earning_status == EarningStatus.payable)).all()
    by_tutor: dict[UUID, list[Lesson]] = defaultdict(list)
    for lesson in rows:
        by_tutor[lesson.tutor_id].append(lesson)
    names = auth_service.full_names(session, by_tutor.keys())
    due = []
    for tutor_id, lessons in by_tutor.items():
        account = _bank(session, tutor_id)
        due_at = min(l.payout_due_at for l in lessons)
        due.append(PayoutDue(
            tutor_id=tutor_id, tutor_name=names.get(tutor_id), lesson_count=len(lessons),
            amount=money(sum((l.tutor_earning for l in lessons), Decimal(0))),
            due_at=due_at, overdue=due_at < now,
            bank_account=BankAccountAdminView.model_validate(account) if account else None,
            can_send=_cleared(account),
        ))
    return sorted(due, key=lambda d: d.due_at)


# ---------- Payouts ----------

def _reads(session: Session, payouts: list[Payout]) -> list[PayoutRead]:
    names = auth_service.full_names(session, [p.tutor_id for p in payouts])
    return [PayoutRead.model_validate(p, update={"tutor_name": names.get(p.tutor_id)}) for p in payouts]


def list_payouts(session: Session, tutor_id: UUID | None, skip: int, limit: int) -> list[PayoutRead]:
    stmt = select(Payout).order_by(Payout.created_at.desc()).offset(skip).limit(limit)
    if tutor_id:
        stmt = stmt.where(Payout.tutor_id == tutor_id)
    return _reads(session, list(session.exec(stmt).all()))


def create_payout(session: Session, admin: User, data: PayoutCreate, now: datetime | None = None) -> PayoutRead:
    """Pays all of the tutor's payable earnings in one payout. Each earning is paid at most once."""
    now = now or clock.now()
    session.exec(select(User.id).where(User.id == data.tutor_id).with_for_update()).one_or_none()
    lessons = session.exec(select(Lesson).where(Lesson.tutor_id == data.tutor_id,
                                                Lesson.earning_status == EarningStatus.payable)
                           .with_for_update()).all()
    if not lessons:
        raise HTTPException(status.HTTP_409_CONFLICT, "This tutor has nothing to be paid")
    amount = money(sum((l.tutor_earning for l in lessons), Decimal(0)))
    payout = Payout(tutor_id=data.tutor_id, amount=amount, lesson_count=len(lessons), method=data.method,
                    status=TransferStatus.processing, reference=payments.new_reference("PO"), note=data.note,
                    created_by=admin.id)

    if data.method == PayoutMethod.paystack:
        account = _bank(session, data.tutor_id)
        if not _cleared(account):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "The tutor's bank details are missing or their name doesn't match")
        if account.recipient_code is None:
            account.recipient_code = paystack.create_transfer_recipient(
                name=account.account_name, account_number=account.account_number, bank_code=account.bank_code,
            )["recipient_code"]
            session.add(account)
        transfer = paystack.initiate_transfer(amount_kobo=to_kobo(amount), recipient_code=account.recipient_code,
                                              reference=payout.reference, reason="TutorLink lesson earnings")
        payout.transfer_code = transfer.get("transfer_code")
        if transfer.get("status") == "success":
            payout.status = TransferStatus.paid
            payout.paid_at = now
    else:
        payout.status = TransferStatus.paid
        payout.paid_at = now

    session.add(payout)
    session.flush()
    for lesson in lessons:
        lesson.earning_status = EarningStatus.paid
        lesson.payout_id = payout.id
        session.add(lesson)
    if payout.status == TransferStatus.paid:
        _notify_paid(session, payout)
    session.commit()
    session.refresh(payout)
    return _reads(session, [payout])[0]


def _notify_paid(session: Session, payout: Payout) -> None:
    notifications.notify(session, payout.tutor_id, "You've been paid",
                         f"{notifications.naira(payout.amount)} for {payout.lesson_count} lesson(s) has been "
                         "sent to your bank account. Your receipt is ready.", f"/receipts/payouts/{payout.id}")


def settle_payout_transfer(session: Session, reference: str, succeeded: bool, now: datetime | None = None) -> None:
    """Outcome of a payout's Paystack transfer. A failed one makes its earnings payable again (spec 1 R6.4)."""
    now = now or clock.now()
    payout = session.exec(select(Payout).where(Payout.reference == reference).with_for_update()).first()
    if payout is None:
        return
    if succeeded and payout.status == TransferStatus.processing:
        payout.status = TransferStatus.paid
        payout.paid_at = now
        _notify_paid(session, payout)
    elif not succeeded and payout.status in (TransferStatus.processing, TransferStatus.paid):
        payout.status = TransferStatus.failed
        payout.paid_at = None
        for lesson in session.exec(select(Lesson).where(Lesson.payout_id == payout.id)).all():
            lesson.earning_status = EarningStatus.payable
            lesson.payout_id = None
            session.add(lesson)
        for admin_id in payments.admin_ids(session):
            notifications.notify(session, admin_id, "Tutor payout failed",
                                 f"A payout of {notifications.naira(payout.amount)} failed; the earnings are "
                                 "payable again.", "/admin/payouts", email=False)
    session.add(payout)


# ---------- Tutor's payouts and receipts ----------

def my_payouts(session: Session, tutor: User) -> list[PayoutRead]:
    rows = session.exec(select(Payout).where(Payout.tutor_id == tutor.id).order_by(Payout.created_at.desc())).all()
    return _reads(session, list(rows))


def payout_receipt(session: Session, user: User, payout_id: UUID) -> PayoutReceipt:
    """The tutor's receipt for a payout, lesson by lesson: agreed price, TutorLink's fee, earning."""
    payout = session.get(Payout, payout_id)
    if payout is None or (user.role != UserRole.admin and payout.tutor_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    if payout.status == TransferStatus.failed:
        raise HTTPException(status.HTTP_409_CONFLICT, "This payout failed, so there is no receipt")
    rows = session.exec(select(Lesson, Booking).join(Booking, Booking.id == Lesson.booking_id)
                        .where(Lesson.payout_id == payout.id).order_by(Lesson.starts_at)).all()
    first_names = {uid: name.split()[0] for uid, name in
                   auth_service.full_names(session, [l.parent_id for l, _ in rows]).items()}
    lines = [PayoutReceiptLine(lesson_date=l.lesson_date, subjects=b.subjects,
                               parent_first_name=first_names.get(l.parent_id, "Parent"), price=l.price,
                               tutor_fee=money(l.price - l.tutor_earning), earning=l.tutor_earning)
             for l, b in rows]
    rates = {b.tutor_fee_rate for _, b in rows}
    account = _bank(session, payout.tutor_id)
    tutor = session.get(User, payout.tutor_id)
    return PayoutReceipt(
        receipt_number=payments.receipt_number(payout.id), issued_at=payout.paid_at or payout.created_at,
        tutor_name=auth_service.full_names(session, [payout.tutor_id]).get(payout.tutor_id), tutor_email=tutor.email,
        method=payout.method, status=payout.status, tutor_fee_rate=rates.pop() if len(rates) == 1 else None,
        bank=f"{account.bank_name} ****{account.account_number[-4:]}"
        if account and payout.method == PayoutMethod.paystack else None,
        lines=lines, total_price=money(sum((x.price for x in lines), Decimal(0))),
        total_fee=money(sum((x.tutor_fee for x in lines), Decimal(0))), total=payout.amount,
    )
