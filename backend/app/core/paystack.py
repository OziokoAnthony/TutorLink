"""Thin client for the Paystack endpoints TutorLink uses. Tests replace these functions with fakes.

Every function returns Paystack's `data` object, or raises 502 when Paystack can't be reached or
refuses the request (except `verify_transaction`, which returns {} for a reference Paystack doesn't know).
"""

import logging
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.paystack.co"


def _request(method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> httpx.Response:
    try:
        return httpx.request(
            method, f"{BASE_URL}{path}", params=params, json=json,
            headers={"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}, timeout=15,
        )
    except httpx.HTTPError:
        logger.exception("Paystack %s %s failed", method, path)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Payment provider unavailable")


def _data(response: httpx.Response, action: str):
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code != 200 or not body.get("status"):
        logger.error("Paystack %s rejected: %s %s", action, response.status_code, body.get("message"))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            f"Payment provider rejected the request: {body.get('message') or 'unknown error'}")
    return body["data"]


def verify_transaction(reference: str) -> dict:
    """Paystack's record of a transaction, or {} if it doesn't know the reference.
    Raises 502 when Paystack can't be reached, so a webhook calling this is retried."""
    response = _request("GET", f"/transaction/verify/{quote(reference, safe='')}")
    if response.status_code >= 500:
        logger.error("Paystack verify failed: %s", response.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Payment provider unavailable")
    try:
        body = response.json()
    except ValueError:
        body = {}
    if response.status_code != 200 or not body.get("status"):
        logger.warning("Paystack verify rejected %s: %s", reference, body.get("message"))
        return {}
    return body["data"]


def create_customer(*, email: str, first_name: str, last_name: str, phone: str | None) -> dict:
    payload = {"email": email, "first_name": first_name, "last_name": last_name}
    if phone:
        payload["phone"] = phone
    return _data(_request("POST", "/customer", json=payload), "create customer")


def create_dedicated_account(customer_code: str) -> dict:
    """Assigns a dedicated account number to an existing customer. Returns account_number,
    account_name and bank{name}."""
    return _data(_request("POST", "/dedicated_account", json={
        "customer": customer_code, "preferred_bank": settings.PAYSTACK_DVA_BANK,
    }), "create dedicated account")


def list_banks() -> list[dict]:
    return _data(_request("GET", "/bank", params={"country": "nigeria", "currency": "NGN", "perPage": 100}),
                 "list banks")


def resolve_account(account_number: str, bank_code: str) -> dict:
    """The name registered on a bank account: {account_number, account_name}."""
    return _data(_request("GET", "/bank/resolve",
                          params={"account_number": account_number, "bank_code": bank_code}),
                 "resolve account")


def create_transfer_recipient(*, name: str, account_number: str, bank_code: str) -> dict:
    return _data(_request("POST", "/transferrecipient", json={
        "type": "nuban", "name": name, "account_number": account_number,
        "bank_code": bank_code, "currency": "NGN",
    }), "create transfer recipient")


def initiate_transfer(*, amount_kobo: int, recipient_code: str, reference: str, reason: str) -> dict:
    """Sends money from the Paystack balance. Returns {transfer_code, status, ...}; the final
    outcome arrives as a transfer.success / transfer.failed / transfer.reversed webhook."""
    return _data(_request("POST", "/transfer", json={
        "source": "balance", "amount": amount_kobo, "recipient": recipient_code,
        "reference": reference, "reason": reason, "currency": "NGN",
    }), "initiate transfer")
