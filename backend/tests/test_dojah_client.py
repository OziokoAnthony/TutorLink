"""The real Dojah client (spec 4 R3.3), with HTTP stubbed: how responses become a NinRecord."""

import base64

import httpx
import pytest
from fastapi import HTTPException

from app.core import dojah
from app.core.config import settings
from app.core.dojah import lookup_nin  # imported before the `dojah` fixture swaps the module attribute


@pytest.fixture
def respond(monkeypatch):
    monkeypatch.setattr(settings, "DOJAH_APP_ID", "app-123")
    monkeypatch.setattr(settings, "DOJAH_SECRET_KEY", "test_sk_123")
    monkeypatch.setattr(settings, "DOJAH_BASE_URL", "https://sandbox.dojah.io/")
    sent = {}

    def answer(status_code: int, body):
        def post(url, json, headers, timeout):
            sent.update(url=url, json=json, headers=headers)
            return httpx.Response(status_code, json=body, request=httpx.Request("POST", url))
        monkeypatch.setattr(dojah.httpx, "post", post)
        return sent
    return answer


def test_nin_response_becomes_a_record(respond):
    sent = respond(200, {"entity": {"nin": "7*****83753", "firstname": "JOHN", "middlename": "DOE",
                                    "surname": "MUSA", "image": "base64-photo", "reference_id": "REF1",
                                    "selfie_verification": {"confidence_value": 99.8, "match": True}}})
    record = lookup_nin("70123456789", b"jpeg-bytes")
    assert (record.first_name, record.middle_name, record.surname) == ("JOHN", "DOE", "MUSA")
    assert record.selfie_matches and record.reference == "REF1"
    assert sent["url"] == "https://sandbox.dojah.io/api/v1/kyc/nin/verify"
    assert sent["headers"] == {"AppId": "app-123", "Authorization": "test_sk_123"}  # no "Bearer"
    assert sent["json"] == {"nin": "70123456789", "selfie_image": base64.b64encode(b"jpeg-bytes").decode()}


def test_low_confidence_or_missing_selfie_result_is_no_match(respond):
    respond(200, {"entity": {"firstname": "JOHN", "surname": "MUSA",
                             "selfie_verification": {"confidence_value": 40.1, "match": False}}})
    assert lookup_nin("70123456789", b"x").selfie_matches is False
    respond(200, {"entity": {"first_name": "JOHN", "last_name": "MUSA"}})
    record = lookup_nin("70123456789", b"x")
    assert record.surname == "MUSA" and record.middle_name == "" and record.selfie_matches is False


@pytest.mark.parametrize("status_code, body", [(404, {"error": "NIN not found"}),
                                               (400, {"error": "Not Found: NIN not found"})])
def test_unknown_nin_is_none(respond, status_code, body):
    respond(status_code, body)
    assert lookup_nin("70123456789", b"x") is None


@pytest.mark.parametrize("status_code, expected", [(400, 422), (401, 502), (402, 502), (500, 502)])
def test_other_errors_are_not_the_tutors_fault_or_a_failed_check(respond, status_code, expected):
    respond(status_code, {"error": "Invalid image"})
    with pytest.raises(HTTPException) as raised:
        lookup_nin("70123456789", b"x")
    assert raised.value.status_code == expected


def test_without_keys_verification_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "DOJAH_APP_ID", "your_dojah_app_id")
    with pytest.raises(HTTPException) as raised:
        lookup_nin("70123456789", b"x")
    assert raised.value.status_code == 503
