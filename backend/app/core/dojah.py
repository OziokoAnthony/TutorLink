"""Dojah NIN lookup with selfie match (spec 4 R3). Every call costs money, so the caller limits attempts.

`POST /api/v1/kyc/nin/verify` takes the NIN and a base64 JPEG selfie and returns the NIN record's name
and `selfie_verification.match`, which Dojah sets when the selfie matches the NIN photo above its
confidence threshold. Nothing returned here is stored except what the caller chooses (R3.7): the
record's photo and the selfie never leave this function.
"""

import base64
import logging
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.core.config import is_placeholder, settings

logger = logging.getLogger(__name__)

PATH = "/api/v1/kyc/nin/verify"


@dataclass
class NinRecord:
    first_name: str
    middle_name: str
    surname: str
    selfie_matches: bool
    reference: str | None


def _unavailable() -> HTTPException:
    return HTTPException(status.HTTP_502_BAD_GATEWAY, "NIN verification isn't available right now. Please try again later.")


def _first(entity: dict, *keys: str) -> str:
    """The NIN response names fields firstname/middlename/surname; Dojah's other lookups use first_name etc."""
    return next((str(entity[k]) for k in keys if entity.get(k)), "")


def lookup_nin(nin: str, selfie_jpeg: bytes) -> NinRecord | None:
    """The NIN record and whether the selfie matches its photo, or None if the NIN doesn't exist."""
    if is_placeholder(settings.DOJAH_APP_ID) or is_placeholder(settings.DOJAH_SECRET_KEY):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "NIN verification isn't available right now")
    try:
        response = httpx.post(
            settings.DOJAH_BASE_URL.rstrip("/") + PATH,
            json={"nin": nin, "selfie_image": base64.b64encode(selfie_jpeg).decode()},
            headers={"AppId": settings.DOJAH_APP_ID, "Authorization": settings.DOJAH_SECRET_KEY},
            timeout=30,
        )
    except httpx.HTTPError:
        logger.exception("Dojah NIN lookup failed")
        raise _unavailable()
    if response.status_code == 404:
        return None
    if response.status_code == 400:
        # Dojah answers 400 both for an unknown NIN and for a bad request; only the first is the tutor's.
        if "not found" in response.text.lower():
            return None
        logger.warning("Dojah refused a NIN lookup: %s", response.text[:200])
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "We couldn't check this NIN and selfie. Check the NIN and retake your selfie.")
    if response.status_code != 200:
        logger.error("Dojah NIN lookup returned %s", response.status_code)
        raise _unavailable()
    entity = response.json().get("entity") or {}
    selfie = entity.get("selfie_verification") or {}
    return NinRecord(
        first_name=_first(entity, "firstname", "first_name"),
        middle_name=_first(entity, "middlename", "middle_name"),
        surname=_first(entity, "surname", "last_name"),
        selfie_matches=selfie.get("match") is True,
        reference=entity.get("reference_id") or response.json().get("reference_id"),
    )
