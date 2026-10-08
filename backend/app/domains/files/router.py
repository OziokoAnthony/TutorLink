"""Serves and receives files in local storage via signed links (development only, while R2 isn't
configured). With R2, the browser reads and uploads with R2's own signed URLs instead."""

import hmac
import time

from fastapi import APIRouter, HTTPException, Request, Response, status

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


@router.put("/{key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def put_file(key: str, request: Request, expires: int, size: int, type: str, sig: str):
    """The local stand-in for an R2 presigned upload: the body must be exactly `size` bytes."""
    if storage.r2_configured():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    expected = storage.local_signature(storage.upload_signing_key(key, type, size), expires)
    if expires < time.time() or not hmac.compare_digest(sig, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Link expired or invalid")
    if request.headers.get("content-type", "").split(";")[0].strip() != type:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Content type doesn't match the upload link")
    try:
        path = storage.local_file(key)
    except ValueError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    written = 0
    with path.open("wb") as out:
        async for chunk in request.stream():
            written += len(chunk)
            if written > size:
                break
            out.write(chunk)
    if written != size:
        path.unlink(missing_ok=True)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "File size doesn't match the upload link")
