from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.scripts.create_admin import create_admin
from tests import helpers


def test_password_hash_roundtrip():
    hashed = get_password_hash("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("wrong", hashed)


def test_expired_token_is_401(client):
    parent = helpers.register_parent(client)
    token = create_access_token(parent["id"], "parent", expires_delta=timedelta(seconds=-1))
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_for_unknown_user_is_401(client):
    token = create_access_token(str(uuid4()), "admin")
    assert client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_create_admin_script(client, db):
    admin = create_admin(db, "Boss@TutorLink.ng", helpers.PASSWORD)
    assert admin.email == "boss@tutorlink.ng"
    me = client.get("/v1/auth/me", headers=helpers.login(client, "boss@tutorlink.ng")).json()
    assert me["user"]["role"] == "admin"
    with pytest.raises(ValueError):
        create_admin(db, "boss@tutorlink.ng", helpers.PASSWORD)


def test_placeholder_secret_key_is_refused():
    # .env.example is public, so its SECRET_KEY would let anyone sign an admin token.
    with pytest.raises(ValidationError, match="placeholder"):
        Settings(SECRET_KEY="your_minimum_32_character_secret_key_here", DATABASE_URL="postgresql://x")
