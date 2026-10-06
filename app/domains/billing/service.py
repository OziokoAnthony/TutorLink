import calendar
import logging
import secrets
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import true as sa_true
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.core.config import settings
from app.domains.auth import service as auth_service
from app.domains.auth.models import ParentProfile, User, UserRole
from app.domains.billing.models import (
    GenerateInvoicesRequest,
    GenerateInvoicesResponse,
    Invoice,
    InvoiceDetail,
    InvoiceItem,
    InvoiceItemRead,
    InvoiceRead,
    InvoiceStatus,
    PaymentInitResponse,
)
from app.domains.notifications import service as notifications
from app.domains.schedules.models import Schedule
from app.domains.sessions.models import SessionStatus, TutoringSession
from app.domains.tutors.models import TutorProfile

logger = logging.getLogger(__name__)

PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
CENT = Decimal("0.01")


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def to_kobo(amount: Decimal) -> int:
    return int(_money(amount) * 100)


def _parent_name(session: Session, parent_id: UUID) -> str:
    profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent_id)).first()
    return profile.full_name if profile else "there"


# ---------- Invoice generation ----------

def generate_invoices(session: Session, data: GenerateInvoicesRequest) -> GenerateInvoicesResponse:
    first_day = date(data.year, data.month, 1)
    last_day = date(data.year, data.month, calendar.monthrange(data.year, data.month)[1])
    rate = settings.COMMISSION_RATE.quantize(Decimal("0.0001"))

    # Business rule 7: only confirmed sessions are billed. The tutor's current rate is
    # captured on the invoice item now and never recalculated (rule 11).
    rows = session.exec(
        select(TutoringSession, Schedule.parent_id, Schedule.tutor_id, TutorProfile.rate_per_session)
        .join(Schedule, Schedule.id == TutoringSession.schedule_id)
        .join(TutorProfile, TutorProfile.user_id == Schedule.tutor_id)
        .where(
            TutoringSession.status == SessionStatus.confirmed,
            TutoringSession.session_date >= first_day,
            TutoringSession.session_date <= last_day,
        )
        .order_by(TutoringSession.session_date)
    ).all()

    by_parent: dict[UUID, list] = defaultdict(list)
    for tutoring_session, parent_id, tutor_id, rate_per_session in rows:
        by_parent[parent_id].append((tutoring_session, tutor_id, rate_per_session))

    already_invoiced = set(session.exec(
        select(Invoice.parent_id).where(
            Invoice.billing_month == data.month, Invoice.billing_year == data.year
        )
    ).all())

    created: list[Invoice] = []
    skipped = 0
    for parent_id, sessions in by_parent.items():
        if parent_id in already_invoiced:  # rule 8: one invoice per parent per month
            skipped += 1
            continue

        subtotal = _money(sum((rate_per_session for _, _, rate_per_session in sessions), Decimal("0")))
        invoice = Invoice(
            parent_id=parent_id,
            billing_month=data.month,
            billing_year=data.year,
            total_sessions=len(sessions),
            subtotal=subtotal,
            commission_rate=rate,
            commission_amount=_money(subtotal * rate),
            total_amount=subtotal,  # parent pays the full amount
        )
        items = [
            InvoiceItem(
                invoice_id=invoice.id,
                session_id=tutoring_session.id,
                tutor_id=tutor_id,
                session_date=tutoring_session.session_date,
                amount=_money(rate_per_session),
                commission_amount=_money(rate_per_session * rate),
            )
            for tutoring_session, tutor_id, rate_per_session in sessions
        ]
        try:
            with session.begin_nested():  # savepoint: a concurrent duplicate only skips this parent
                session.add(invoice)
                session.flush()
                session.add_all(items)
        except IntegrityError:
            skipped += 1
            continue
        created.append(invoice)

    session.commit()
    for invoice in created:
        session.refresh(invoice)
        parent = session.get(User, invoice.parent_id)
        notifications.invoice_generated(parent.email, _parent_name(session, parent.id), invoice.billing_month,
                                        invoice.billing_year, invoice.total_sessions, invoice.total_amount)

    parents_without_sessions = session.exec(
        select(func.count()).select_from(User).where(
            User.role == UserRole.parent,
            User.is_active == True,  # noqa: E712
            User.id.not_in(list(by_parent)) if by_parent else sa_true(),
        )
    ).one()
    names = auth_service.full_names(session, [i.parent_id for i in created])
    return GenerateInvoicesResponse(
        created=len(created),
        skipped_existing=skipped,
        parents_without_sessions=parents_without_sessions,
        invoices=[InvoiceRead.model_validate(i, update={"parent_name": names.get(i.parent_id)}) for i in created],
    )


# ---------- Parent views ----------

def _get_own_invoice(session: Session, parent: User, invoice_id: UUID, *, lock: bool = False) -> Invoice:
    invoice = session.get(Invoice, invoice_id, with_for_update=lock)
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    if invoice.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own invoices")
    return invoice


def list_my_invoices(session: Session, parent: User) -> list[InvoiceRead]:
    invoices = session.exec(
        select(Invoice)
        .where(Invoice.parent_id == parent.id)
        .order_by(Invoice.billing_year.desc(), Invoice.billing_month.desc())
    ).all()
    return [InvoiceRead.model_validate(i) for i in invoices]


def get_invoice_detail(session: Session, parent: User, invoice_id: UUID) -> InvoiceDetail:
    invoice = _get_own_invoice(session, parent, invoice_id)
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.session_date)
    ).all()
    return InvoiceDetail.model_validate(
        invoice, update={"items": [InvoiceItemRead.model_validate(i) for i in items]}
    )


# ---------- Payment ----------

def initialize_paystack_transaction(*, email: str, amount_kobo: int, reference: str,
                                    callback_url: str, metadata: dict) -> dict:
    """Calls Paystack's Initialize Transaction API and returns its `data` object."""
    try:
        response = httpx.post(
            PAYSTACK_INITIALIZE_URL,
            json={
                "email": email,
                "amount": amount_kobo,
                "currency": "NGN",
                "reference": reference,
                "callback_url": callback_url,
                "metadata": metadata,
            },
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"},
            timeout=15,
        )
        body = response.json()
    except (httpx.HTTPError, ValueError):
        logger.exception("Paystack initialize request failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Payment provider unavailable")

    if response.status_code != 200 or not body.get("status"):
        logger.error("Paystack initialize rejected: %s %s", response.status_code, body.get("message"))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Payment provider rejected the request")
    return body["data"]


def pay_invoice(session: Session, parent: User, invoice_id: UUID) -> PaymentInitResponse:
    invoice = _get_own_invoice(session, parent, invoice_id, lock=True)
    # Rule 9: never charge a paid invoice. A failed invoice can be retried; it goes back to pending.
    if invoice.status == InvoiceStatus.paid:
        raise HTTPException(status.HTTP_409_CONFLICT, "Invoice is already paid")

    # Paystack rejects reused references, so every attempt gets a fresh one.
    reference = f"TL-{invoice.id.hex[:12]}-{secrets.token_hex(4)}"
    data = initialize_paystack_transaction(
        email=parent.email,
        amount_kobo=to_kobo(invoice.total_amount),
        reference=reference,
        callback_url=f"{settings.FRONTEND_URL}/dashboard/parent/invoices?invoice={invoice.id}",
        metadata={"invoice_id": str(invoice.id)},
    )
    invoice.paystack_reference = reference
    invoice.status = InvoiceStatus.pending
    session.add(invoice)
    session.commit()
    return PaymentInitResponse(authorization_url=data["authorization_url"], reference=reference)
