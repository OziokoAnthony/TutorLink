import hashlib
import hmac
import json
import logging
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, select

from app.core.config import settings
from app.db.base import utcnow
from app.domains.auth.models import ParentProfile, User
from app.domains.billing.models import Invoice, InvoiceStatus
from app.domains.billing.service import to_kobo
from app.domains.notifications import service as notifications
from app.domains.webhooks.models import WebhookEvent

logger = logging.getLogger(__name__)


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(settings.PAYSTACK_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def _event_id(payload: dict, header_event_id: str | None) -> str | None:
    """Use the event id header when present. Paystack doesn't document one, so otherwise
    fall back to `<event>:<transaction id>`, which is unique per event and stable on retries."""
    if header_event_id:
        return header_event_id
    data = payload.get("data") or {}
    transaction_id = data.get("id") or data.get("reference")
    if not payload.get("event") or not transaction_id:
        return None
    return f"{payload['event']}:{transaction_id}"


def _find_invoice(session: Session, data: dict) -> Invoice | None:
    reference = data.get("reference")
    invoice = None
    if reference:
        invoice = session.exec(
            select(Invoice).where(Invoice.paystack_reference == reference).with_for_update()
        ).first()
    if invoice is None:
        # A parent can start several payment attempts; only the latest reference is stored,
        # so fall back to the invoice id we put in the transaction metadata.
        metadata = data.get("metadata")
        invoice_id = metadata.get("invoice_id") if isinstance(metadata, dict) else None
        try:
            invoice = session.get(Invoice, UUID(invoice_id), with_for_update=True) if invoice_id else None
        except ValueError:
            invoice = None
    return invoice


def _mark_paid(session: Session, data: dict) -> Invoice | None:
    invoice = _find_invoice(session, data)
    if invoice is None:
        logger.warning("charge.success for unknown invoice (reference=%s)", data.get("reference"))
        return None
    if invoice.status == InvoiceStatus.paid:
        return None
    if data.get("amount") != to_kobo(invoice.total_amount) or data.get("currency", "NGN") != "NGN":
        logger.warning("charge.success amount mismatch for invoice %s: got %s %s",
                       invoice.id, data.get("amount"), data.get("currency"))
        return None

    invoice.status = InvoiceStatus.paid
    invoice.paid_at = utcnow()
    invoice.paystack_reference = data.get("reference") or invoice.paystack_reference
    session.add(invoice)
    return invoice


def _mark_failed(session: Session, data: dict) -> None:
    reference = data.get("reference")
    if not reference:
        return
    invoice = session.exec(
        select(Invoice).where(Invoice.paystack_reference == reference).with_for_update()
    ).first()
    # Only the latest payment attempt counts: a failure on an older reference, or after the
    # invoice was paid, changes nothing.
    if invoice is not None and invoice.status == InvoiceStatus.pending:
        invoice.status = InvoiceStatus.failed
        session.add(invoice)


def process_payment_webhook(session: Session, raw_body: bytes, signature: str | None,
                            header_event_id: str | None) -> dict:
    # 1-2. Signature is checked against the raw bytes, before any JSON parsing.
    if not verify_signature(raw_body, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
    try:
        payload = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid JSON")

    event_id = _event_id(payload, header_event_id)
    if event_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot identify event")
    event_type = payload.get("event", "")

    # 3-4. Idempotency: the insert and the invoice update commit together, so an event is
    # only recorded once it has been fully processed.
    inserted = session.connection().execute(
        pg_insert(WebhookEvent)
        .values(id=uuid4(), event_id=event_id, event_type=event_type, processed_at=utcnow())
        .on_conflict_do_nothing(index_elements=["event_id"])
        .returning(WebhookEvent.id)
    ).first()
    if inserted is None:
        session.rollback()
        return {"status": "duplicate"}

    # 5-6. Mark the invoice paid (or failed, so the parent can retry).
    data = payload.get("data") or {}
    invoice = None
    if event_type == "charge.success":
        invoice = _mark_paid(session, data)
    elif event_type == "charge.failed":
        _mark_failed(session, data)
    session.commit()

    # 7. Confirmation email.
    if invoice is not None:
        session.refresh(invoice)
        parent = session.get(User, invoice.parent_id)
        profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == parent.id)).first()
        notifications.payment_received(parent.email, profile.full_name if profile else "there",
                                       invoice.billing_month, invoice.billing_year, invoice.total_amount)
    return {"status": "ok"}
