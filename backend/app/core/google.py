"""Google sign-in (spec 4 R1): verifies the ID token the browser gets from Google Identity Services.

The token is a JWT signed by Google. We check its signature against Google's published keys, that it
was issued for our Client ID, by Google, hasn't expired, and that Google verified the email (R1.5).
"""

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import HTTPException, status

from app.core.config import is_placeholder, settings

logger = logging.getLogger(__name__)

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
PHOTO_MAX_BYTES = 5 * 1024 * 1024

_jwks = jwt.PyJWKClient(CERTS_URL, cache_keys=True, lifespan=6 * 60 * 60)


@dataclass
class GoogleIdentity:
    email: str  # lowercase, verified by Google
    given_name: str | None
    family_name: str | None
    name: str | None
    picture: str | None


def signing_key(token: str):
    """The Google public key that signed `token` (by its `kid`). Tests replace this."""
    return _jwks.get_signing_key_from_jwt(token).key


def _refused(detail: str = "Google sign-in failed. Please try again.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


def verify_id_token(token: str) -> GoogleIdentity:
    if is_placeholder(settings.GOOGLE_CLIENT_ID):
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google sign-in isn't available right now")
    try:
        claims = jwt.decode(token, signing_key(token), algorithms=["RS256"], audience=settings.GOOGLE_CLIENT_ID,
                            options={"require": ["exp", "iss", "aud", "email"]})
    except jwt.PyJWKClientConnectionError:
        logger.exception("Could not fetch Google's signing keys")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Google sign-in isn't available right now")
    except jwt.PyJWTError:
        raise _refused()
    if claims["iss"] not in ISSUERS:
        raise _refused()
    if claims.get("email_verified") is not True:
        raise _refused("Your Google email address isn't verified")
    return GoogleIdentity(email=claims["email"].lower(), given_name=claims.get("given_name"),
                          family_name=claims.get("family_name"), name=claims.get("name"),
                          picture=claims.get("picture"))


def is_google_photo_url(url: str | None) -> bool:
    """Only Google's own image host is fetched, though the URL comes from a token Google signed."""
    parsed = urlparse(url or "")
    return parsed.scheme == "https" and (parsed.hostname or "").endswith(".googleusercontent.com")


def fetch_photo(url: str | None) -> bytes | None:
    """The Google account photo (R1b.3), or None if there is none or it can't be fetched."""
    if not is_google_photo_url(url):
        return None
    try:
        with httpx.stream("GET", url, timeout=10, follow_redirects=False) as response:
            response.raise_for_status()
            data = b""
            for chunk in response.iter_bytes():
                data += chunk
                if len(data) > PHOTO_MAX_BYTES:
                    return None
            return data
    except httpx.HTTPError:
        logger.warning("Could not fetch the Google account photo")
        return None
