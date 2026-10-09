"""Google sign-in (spec 4 R1): parents and tutors may register and log in with Google, as well as with
any email and a password. Plus "Forgot password?" (R0.7)."""

import re
from datetime import timedelta

from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from tests import helpers
from tests.helpers import PASSWORD, google_token


def google_login(client, token):
    return client.post("/v1/auth/google/login", json={"id_token": token})


def password_login(client, email, password=PASSWORD):
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- Token verification (R1.5) ----------

def bad_tokens(email):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {
        "forged": google_token(email, key=other_key),
        "expired": google_token(email, expires_in=timedelta(minutes=-5)),
        "wrong audience": google_token(email, aud="someone-else.apps.googleusercontent.com"),
        "wrong issuer": google_token(email, iss="https://evil.example.com"),
        "unverified email": google_token(email, email_verified=False),
        "not a jwt": "not-a-token",
    }


def test_bad_google_tokens_are_401_on_login_and_registration(client):
    parent = helpers.register_parent(client, email="ada@example.com")
    for name, token in bad_tokens(parent["email"]).items():
        assert google_login(client, token).status_code == 401, name
        assert helpers.google_register(client, "new@example.com", id_token=token).status_code == 401, name
        assert helpers.google_register(client, "new@example.com", "parent",
                                       id_token=token).status_code == 401, name


def test_google_sign_in_is_unavailable_without_a_client_id(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "your_google_client_id.apps.googleusercontent.com")
    assert google_login(client, google_token("ada@example.com")).status_code == 503


# ---------- Tutors (R1.1-R1.3) ----------

def test_tutor_registration_needs_a_google_token(client):
    body = {"role": "tutor", "first_name": "Anthony", "surname": "Ozioko", "area": "Lekki",
            "offers": [helpers.offer()]}
    assert client.post("/v1/auth/google/register", json=body).status_code == 422


def test_tutor_registers_with_google_and_is_signed_in(client, outbox):
    response = helpers.google_register(client, "Anthony@Gmail.com")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["email"] == "anthony@gmail.com"  # the Google email is their email
    assert "work_email" not in body["user"] and "password" not in body
    assert body["tutor_profile"]["vetting_status"] == "pending"
    me = client.get("/v1/auth/me", headers=bearer(body["access_token"])).json()
    assert me["user"]["role"] == "tutor"

    email = outbox[-1]
    assert email["to"] == "anthony@gmail.com" and "application" in email["subject"]


def test_tutor_logs_in_with_google(client):
    tutor = helpers.register_tutor(client, email="anthony@gmail.com")
    response = google_login(client, google_token("anthony@gmail.com"))
    assert response.status_code == 200
    me = client.get("/v1/auth/me", headers=bearer(response.json()["access_token"])).json()
    assert me["user"]["id"] == tutor["id"]


def test_tutor_registration_with_a_used_google_email_is_409(client):
    helpers.register_tutor(client, email="anthony@gmail.com")
    assert helpers.google_register(client, "anthony@gmail.com").status_code == 409


def test_tutor_fields_are_still_required_with_google(client):
    assert helpers.google_register(client, "a@gmail.com", area=None).status_code == 422
    assert helpers.google_register(client, "a@gmail.com", offers=[]).status_code == 422
    assert helpers.google_register(client, "a@gmail.com", surname=" ").status_code == 422


# ---------- Parents (R1.4) ----------

def test_parent_google_login_signs_into_the_existing_parent_account(client):
    parent = helpers.register_parent(client, email="ada@example.com")
    response = google_login(client, google_token("ADA@example.com"))
    assert response.status_code == 200
    me = client.get("/v1/auth/me", headers=bearer(response.json()["access_token"])).json()
    assert me["user"]["id"] == parent["id"]


def test_parent_google_login_for_a_new_email_asks_them_to_sign_up(client):
    response = google_login(client, google_token("new@example.com"))
    assert response.status_code == 404
    assert "Sign up" in response.json()["detail"]


def test_parent_google_sign_up_needs_the_profile_fields_and_signs_them_in(client):
    assert helpers.google_register(client, "new@example.com", "parent", full_name=None).status_code == 422
    response = helpers.google_register(client, "new@example.com", "parent", full_name="Ada Obi",
                                       address="12 Allen Avenue")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parent_profile"]["full_name"] == "Ada Obi"
    me = client.get("/v1/auth/me", headers=bearer(body["access_token"])).json()
    assert me["user"]["email"] == "new@example.com"
    assert google_login(client, google_token("new@example.com")).status_code == 200


def test_parent_who_signed_up_with_google_has_no_password(client):
    token = helpers.google_register(client, "new@example.com", "parent").json()["access_token"]
    assert password_login(client, "new@example.com", "anything-at-all").status_code == 401
    response = client.put("/v1/auth/me/password", headers=bearer(token),
                          json={"current_password": "", "new_password": "my-new-password"})
    assert response.status_code == 422
    assert "Forgot password" in response.json()["detail"]


def test_admins_cannot_sign_in_with_google(client, db):
    from app.scripts.create_admin import create_admin
    create_admin(db, "boss@example.com", PASSWORD)
    assert google_login(client, google_token("boss@example.com")).status_code == 401


# ---------- One role per email (R1.6) ----------

def test_a_google_email_of_the_other_role_is_409(client):
    helpers.register_parent(client, email="parent@example.com")
    response = helpers.google_register(client, "parent@example.com", "tutor")
    assert response.status_code == 409
    assert "parent" in response.json()["detail"]

    helpers.register_tutor(client, email="tutor@example.com")
    assert helpers.google_register(client, "tutor@example.com", "parent").status_code == 409
    body = {"email": "tutor@example.com", "password": PASSWORD, "role": "parent", "full_name": "Ada Parent"}
    assert client.post("/v1/auth/register", json=body).status_code == 409


# ---------- Google photo (R1b.3) ----------

def test_google_photo_is_the_starting_picture_when_asked(client, google):
    with_photo = helpers.google_register(client, "a@example.com", "parent", use_google_photo=True).json()
    assert with_photo["user"]["photo_url"]
    assert google.fetched == ["https://lh3.googleusercontent.com/a/photo"]

    without = helpers.google_register(client, "b@example.com", "parent").json()
    assert without["user"]["photo_url"] is None

    google.photo = None  # Google has no photo, or it couldn't be fetched
    unavailable = helpers.google_register(client, "c@example.com", "parent", use_google_photo=True)
    assert unavailable.status_code == 201
    assert unavailable.json()["user"]["photo_url"] is None


def test_google_photo_fetch_only_reaches_google_image_hosts():
    from app.core.google import is_google_photo_url
    assert is_google_photo_url("https://lh3.googleusercontent.com/a/photo")
    assert not is_google_photo_url("https://evil.example.com/a.png")
    assert not is_google_photo_url("https://googleusercontent.com.evil.example.com/a.png")
    assert not is_google_photo_url("http://lh3.googleusercontent.com/a")
    assert not is_google_photo_url(None)


# ---------- Forgot password (R0.7) ----------

def forgot(client, email):
    return client.post("/v1/auth/forgot-password", json={"email": email})


def reset(client, token, password="brand-new-password"):
    return client.post("/v1/auth/reset-password", json={"token": token, "new_password": password})


def link_token(email: dict) -> str:
    return re.search(r"reset-password\?token=([\w-]+)", email["html"]).group(1)


def test_forgot_password_answers_the_same_for_known_and_unknown_emails(client, outbox):
    helpers.register_parent(client, email="ada@example.com")
    sent_before = len(outbox)
    known, unknown = forgot(client, "ada@example.com"), forgot(client, "nobody@example.com")
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert [e["to"] for e in outbox[sent_before:]] == ["ada@example.com"]


def test_parent_reset_email_has_a_link(client, outbox):
    helpers.register_parent(client, email="ada@example.com")
    forgot(client, "ada@example.com")
    assert link_token(outbox[-1])


def test_reset_link_sets_a_new_password_once(client, outbox):
    tutor = helpers.register_tutor(client, email="anthony@gmail.com")
    forgot(client, "anthony@gmail.com")
    token = link_token(outbox[-1])

    assert reset(client, token).status_code == 204
    assert password_login(client, tutor["email"]).status_code == 401  # the old password stops working
    assert password_login(client, tutor["email"], "brand-new-password").status_code == 200
    # Every session is ended, so whoever knew the old password is logged out too.
    assert client.get("/v1/auth/me", headers=tutor["headers"]).status_code == 401

    assert reset(client, token, "another-password").status_code == 422  # works once


def test_reset_link_expires_after_an_hour(client, outbox, clock):
    helpers.register_parent(client, email="ada@example.com")
    forgot(client, "ada@example.com")
    token = link_token(outbox[-1])
    clock.travel(minutes=61)
    assert reset(client, token).status_code == 422
    assert password_login(client, "ada@example.com").status_code == 200


def test_using_a_reset_link_cancels_older_ones(client, outbox):
    helpers.register_parent(client, email="ada@example.com")
    forgot(client, "ada@example.com")
    older = link_token(outbox[-1])
    forgot(client, "ada@example.com")
    assert reset(client, link_token(outbox[-1])).status_code == 204
    assert reset(client, older).status_code == 422


def test_unknown_reset_token_is_422(client):
    assert reset(client, "made-up-token").status_code == 422


def test_reset_password_needs_eight_characters(client, outbox):
    helpers.register_parent(client, email="ada@example.com")
    forgot(client, "ada@example.com")
    assert reset(client, link_token(outbox[-1]), "short").status_code == 422


def test_parent_who_signed_up_with_google_sets_a_password_by_reset(client, outbox):
    helpers.google_register(client, "new@example.com", "parent")
    forgot(client, "new@example.com")
    assert reset(client, link_token(outbox[-1])).status_code == 204
    assert password_login(client, "new@example.com", "brand-new-password").status_code == 200


def test_admins_get_no_reset_email(client, db, outbox):
    from app.scripts.create_admin import create_admin
    create_admin(db, "boss@example.com", PASSWORD)
    sent_before = len(outbox)
    assert forgot(client, "boss@example.com").status_code == 202
    assert len(outbox) == sent_before


def test_reset_tokens_are_stored_only_as_hashes(client, db, outbox):
    from sqlmodel import select

    from app.domains.auth.models import PasswordResetToken
    helpers.register_parent(client, email="ada@example.com")
    forgot(client, "ada@example.com")
    token = link_token(outbox[-1])
    stored = db.exec(select(PasswordResetToken)).one()
    assert stored.token_hash != token and token not in stored.token_hash
