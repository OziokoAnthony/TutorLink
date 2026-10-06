import hashlib
import hmac
import json

import pytest
from sqlmodel import select

from app.core.config import settings
from app.domains.webhooks.models import WebhookEvent
from tests import helpers


def sign(body: bytes) -> str:
    return hmac.new(settings.PAYSTACK_WEBHOOK_SECRET.encode(), body, hashlib.sha512).hexdigest()


def post_webhook(client, payload: dict, signature: str | None = None):
    body = json.dumps(payload).encode()
    return client.post("/v1/webhooks/payment", content=body, headers={
        "Content-Type": "application/json",
        "X-Paystack-Signature": signature if signature is not None else sign(body),
    })


@pytest.fixture
def unpaid_invoice(client, admin_headers, paystack):
    """A parent with a 5,000 NGN invoice for October 2025 and a started Paystack payment."""
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers, rate="5000.00")
    schedule = helpers.booked_schedule(client, parent, tutor)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    invoice = client.post("/v1/invoices/generate", headers=admin_headers,
                          json={"month": 10, "year": 2025}).json()["invoices"][0]
    reference = client.post(f"/v1/invoices/{invoice['id']}/pay", headers=parent["headers"]).json()["reference"]
    return {"parent": parent, "id": invoice["id"], "reference": reference}


def charge_success(reference: str, amount: int = 500000, transaction_id: int = 4099260516) -> dict:
    return {"event": "charge.success",
            "data": {"id": transaction_id, "reference": reference, "amount": amount, "currency": "NGN"}}


def invoice_status(client, invoice) -> str:
    return client.get(f"/v1/invoices/{invoice['id']}", headers=invoice["parent"]["headers"]).json()["status"]


def test_valid_signature_charge_success_marks_invoice_paid(client, unpaid_invoice):
    response = post_webhook(client, charge_success(unpaid_invoice["reference"]))
    assert response.status_code == 200
    detail = client.get(f"/v1/invoices/{unpaid_invoice['id']}", headers=unpaid_invoice["parent"]["headers"]).json()
    assert detail["status"] == "paid"
    assert detail["paid_at"] is not None


def test_invalid_signature_is_401_and_not_processed(client, db, unpaid_invoice):
    response = post_webhook(client, charge_success(unpaid_invoice["reference"]), signature="deadbeef")
    assert response.status_code == 401
    assert invoice_status(client, unpaid_invoice) == "pending"
    assert db.exec(select(WebhookEvent)).all() == []


def test_missing_signature_is_401(client, unpaid_invoice):
    body = json.dumps(charge_success(unpaid_invoice["reference"])).encode()
    assert client.post("/v1/webhooks/payment", content=body).status_code == 401


def test_duplicate_event_returns_200_and_is_processed_once(client, db, unpaid_invoice, outbox):
    payload = charge_success(unpaid_invoice["reference"])
    assert post_webhook(client, payload).json() == {"status": "ok"}
    second = post_webhook(client, payload)
    assert second.status_code == 200
    assert second.json() == {"status": "duplicate"}
    assert len(db.exec(select(WebhookEvent)).all()) == 1
    assert [e["subject"] for e in outbox].count("Payment received — thank you!") == 1


def test_older_payment_reference_still_matches_via_metadata(client, unpaid_invoice):
    # The parent started a second attempt, so the stored reference changed; the first one gets paid.
    client.post(f"/v1/invoices/{unpaid_invoice['id']}/pay", headers=unpaid_invoice["parent"]["headers"])
    payload = charge_success(unpaid_invoice["reference"])
    payload["data"]["metadata"] = {"invoice_id": unpaid_invoice["id"]}
    post_webhook(client, payload)
    assert invoice_status(client, unpaid_invoice) == "paid"


def test_amount_mismatch_does_not_mark_paid(client, unpaid_invoice):
    assert post_webhook(client, charge_success(unpaid_invoice["reference"], amount=100)).status_code == 200
    assert invoice_status(client, unpaid_invoice) == "pending"


def test_paid_invoice_cannot_be_paid_again(client, unpaid_invoice):
    post_webhook(client, charge_success(unpaid_invoice["reference"]))
    response = client.post(f"/v1/invoices/{unpaid_invoice['id']}/pay", headers=unpaid_invoice["parent"]["headers"])
    assert response.status_code == 409


def charge_failed(reference: str, transaction_id: int = 4099260999) -> dict:
    return {"event": "charge.failed",
            "data": {"id": transaction_id, "reference": reference, "amount": 500000, "currency": "NGN"}}


def test_charge_failed_marks_invoice_failed_and_parent_can_retry(client, unpaid_invoice):
    assert post_webhook(client, charge_failed(unpaid_invoice["reference"])).status_code == 200
    assert invoice_status(client, unpaid_invoice) == "failed"

    retry = client.post(f"/v1/invoices/{unpaid_invoice['id']}/pay", headers=unpaid_invoice["parent"]["headers"])
    assert retry.status_code == 200
    assert invoice_status(client, unpaid_invoice) == "pending"

    post_webhook(client, charge_success(retry.json()["reference"]))
    assert invoice_status(client, unpaid_invoice) == "paid"


def test_charge_failed_for_an_older_attempt_is_ignored(client, unpaid_invoice):
    client.post(f"/v1/invoices/{unpaid_invoice['id']}/pay", headers=unpaid_invoice["parent"]["headers"])
    post_webhook(client, charge_failed(unpaid_invoice["reference"]))  # first attempt's reference
    assert invoice_status(client, unpaid_invoice) == "pending"


def test_charge_failed_after_payment_does_not_unpay(client, unpaid_invoice):
    post_webhook(client, charge_success(unpaid_invoice["reference"]))
    post_webhook(client, charge_failed(unpaid_invoice["reference"]))
    assert invoice_status(client, unpaid_invoice) == "paid"


def test_other_events_are_recorded_and_acknowledged(client, db, unpaid_invoice):
    payload = {"event": "transfer.success", "data": {"id": 1, "reference": "TRF-1"}}
    assert post_webhook(client, payload).status_code == 200
    assert invoice_status(client, unpaid_invoice) == "pending"
    assert db.exec(select(WebhookEvent.event_type)).all() == ["transfer.success"]
