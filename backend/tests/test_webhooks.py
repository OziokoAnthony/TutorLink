"""The Paystack webhook: signatures, once-only processing, and re-checking every deposit with Paystack."""

import json

import pytest
from sqlmodel import select

from app.core.config import settings
from app.domains.webhooks.models import WebhookEvent
from tests import helpers


@pytest.fixture
def parent(client):
    """A parent who already has an account number."""
    parent = helpers.register_parent(client)
    assert client.post("/v1/wallet/me/account-number", headers=parent["headers"]).status_code == 200
    return parent


def balance(client, parent) -> str:
    return client.get("/v1/wallet/me", headers=parent["headers"]).json()["balance"]


def deposit_payload(paystack, parent, reference="DEP-1", naira="2000.00") -> dict:
    return {"event": "charge.success", "data": {
        "id": 4099260516, "reference": reference, "amount": int(float(naira) * 100), "currency": "NGN",
        "channel": "dedicated_nuban", "customer": {"customer_code": paystack.customers[parent["email"]]},
    }}


def test_valid_deposit_credits_the_balance(client, paystack, parent):
    assert helpers.deposit(client, paystack, parent, "2000.00").status_code == 200
    assert balance(client, parent) == "2000.00"


def test_invalid_signature_is_401_and_not_processed(client, db, paystack, parent):
    response = helpers.post_webhook(client, deposit_payload(paystack, parent), signature="deadbeef")
    assert response.status_code == 401
    assert balance(client, parent) == "0.00"
    assert db.exec(select(WebhookEvent)).all() == []


def test_missing_signature_is_401(client, paystack, parent):
    body = json.dumps(deposit_payload(paystack, parent)).encode()
    assert client.post("/v1/webhooks/payment", content=body).status_code == 401


@pytest.mark.parametrize("secret", ["", "whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"])
def test_unconfigured_webhook_secret_rejects_every_event(client, db, monkeypatch, paystack, parent, secret):
    monkeypatch.setattr(settings, "PAYSTACK_WEBHOOK_SECRET", secret)
    assert helpers.deposit(client, paystack, parent, "2000.00").status_code == 503
    assert db.exec(select(WebhookEvent)).all() == []


def test_duplicate_event_is_processed_once(client, db, paystack, parent):
    payload = deposit_payload(paystack, parent)
    paystack.transactions["DEP-1"] = {**payload["data"], "status": "success"}
    assert helpers.post_webhook(client, payload).json() == {"status": "ok"}
    assert helpers.post_webhook(client, payload).json() == {"status": "duplicate"}
    assert balance(client, parent) == "2000.00"
    assert len(db.exec(select(WebhookEvent)).all()) == 1


def test_same_reference_in_a_different_event_is_not_credited_twice(client, paystack, parent):
    helpers.deposit(client, paystack, parent, "2000.00", reference="DEP-SAME")
    payload = deposit_payload(paystack, parent, reference="DEP-SAME")
    payload["data"]["id"] = 1  # a different event id, same transfer
    helpers.post_webhook(client, payload)
    assert balance(client, parent) == "2000.00"


def test_deposit_not_confirmed_by_paystack_is_not_credited(client, paystack, parent):
    assert helpers.deposit(client, paystack, parent, "2000.00", confirmed=False).status_code == 200
    assert balance(client, parent) == "0.00"


def test_deposit_with_a_different_amount_at_paystack_uses_paystacks_amount(client, paystack, parent):
    payload = deposit_payload(paystack, parent, naira="900000.00")  # forged amount in the event
    paystack.transactions["DEP-1"] = {**payload["data"], "amount": 100000, "status": "success"}
    helpers.post_webhook(client, payload)
    assert balance(client, parent) == "1000.00"


def test_deposit_for_unknown_customer_is_ignored(client, paystack, parent):
    payload = deposit_payload(paystack, parent)
    payload["data"]["customer"]["customer_code"] = "CUS_unknown"
    assert helpers.post_webhook(client, payload).status_code == 200
    assert balance(client, parent) == "0.00"


def test_paystack_unreachable_is_502_and_the_retry_is_processed(client, db, paystack, parent):
    payload = deposit_payload(paystack, parent)
    paystack.transactions["DEP-1"] = {**payload["data"], "status": "success"}
    paystack.unreachable = True
    assert helpers.post_webhook(client, payload).status_code == 502
    assert db.exec(select(WebhookEvent)).all() == []
    paystack.unreachable = False
    assert helpers.post_webhook(client, payload).json() == {"status": "ok"}
    assert balance(client, parent) == "2000.00"


def test_other_events_are_recorded_and_acknowledged(client, db):
    payload = {"event": "subscription.create", "data": {"id": 1, "reference": "SUB-1"}}
    assert helpers.post_webhook(client, payload).status_code == 200
    assert db.exec(select(WebhookEvent.event_type)).all() == ["subscription.create"]
