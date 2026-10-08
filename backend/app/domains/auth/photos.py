"""Profile pictures (spec 4 R1b): upload, resize, and short-lived links to show them."""

import io
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlmodel import Session, select

from app.core import storage
from app.domains.auth.models import User

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
SIZE = 512
URL_SECONDS = 6 * 60 * 60  # long enough that an open page doesn't show broken pictures


def url_for(user: User) -> str | None:
    return storage.url(user.photo_key, URL_SECONDS) if user.photo_key else None


def urls_for(session: Session, user_ids) -> dict[UUID, str]:
    """user id -> photo URL, for users who have a picture (one query for any number of ids)."""
    ids = list({uid for uid in user_ids if uid is not None})
    if not ids:
        return {}
    rows = session.exec(select(User.id, User.photo_key).where(User.id.in_(ids), User.photo_key.is_not(None))).all()
    return {uid: storage.url(key, URL_SECONDS) for uid, key in rows}


def _square_jpeg(data: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(data))
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The file is not a JPG, PNG or WebP image")
    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Profile pictures must be JPG, PNG or WebP")
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, (SIZE, SIZE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    image.save(out, "JPEG", quality=85)
    return out.getvalue()


def read_upload(file: UploadFile) -> bytes:
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Profile pictures can be at most 5 MB")
    return data


def set_photo(session: Session, user: User, data: bytes) -> str:
    jpeg = _square_jpeg(data)
    key = f"photos/{user.id}/{uuid4().hex}.jpg"
    storage.save(key, jpeg, "image/jpeg")
    old_key = user.photo_key
    user.photo_key = key
    session.add(user)
    session.commit()
    if old_key:
        storage.delete(old_key)
    return url_for(user)


def remove_photo(session: Session, user: User) -> None:
    """Admin removal of an inappropriate picture: the user must upload a new one."""
    if user.photo_key:
        storage.delete(user.photo_key)
        user.photo_key = None
        session.add(user)
        session.commit()
