"""Serves files from local storage via signed links (development only, while R2 isn't configured)."""

import hmac
import time

from fastapi import APIRouter, HTTPException, Response, status

from app.core import storage

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{key:path}")
def get_file(key: str, expires: int, sig: str):
    if storage.r2_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    if expires < time.time() or not hmac.compare_digest(sig, storage.local_signature(key, expires)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    try:
        found = storage.read_local(key)
    except ValueError:
        found = None
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    data, content_type = found
    return Response(data, media_type=content_type, headers={"Cache-Control": "private, max-age=3600"})
