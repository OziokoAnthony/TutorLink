import hashlib
import hmac
import json
import logging
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session

from app.core.config import is_placeholder, settings
from app.db.base import utcnow
from app.domains.bookings import service as bookings
from app.domains.payments import service as payments
from app.domains.payouts import service as payouts
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


def process_payment_webhook(session: Session, raw_body: bytes, signature: str | None,
                            header_event_id: str | None) -> dict:
    # With an empty or public example secret, anyone could sign a fake "payment succeeded" event.
    if is_placeholder(settings.PAYSTACK_WEBHOOK_SECRET):
        logger.error("PAYSTACK_WEBHOOK_SECRET is not set; rejecting payment webhook")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Payment webhooks are not configured")

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

    # 3-4. Idempotency: the insert and the money movement commit together, so an event is
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

    # 5. Apply it. Deposits are matched to the parent by their account number's Paystack customer.
    data = payload.get("data") or {}
    parent_id = None
    if event_type == "charge.success":
        parent_id = payments.credit_deposit(session, data)
    elif event_type in ("transfer.success", "transfer.failed", "transfer.reversed"):
        reference = str(data.get("reference") or "")
        succeeded = event_type == "transfer.success"
        if reference.startswith("PO-"):
            payouts.settle_payout_transfer(session, reference, succeeded)
        elif reference.startswith("WD-"):
            payments.settle_withdrawal_transfer(session, reference, succeeded)
    session.commit()

    # 6. New money may cover lessons waiting to be paid.
    if parent_id is not None:
        bookings.pay_due_periods(session, parent_id)
    return {"status": "ok"}
