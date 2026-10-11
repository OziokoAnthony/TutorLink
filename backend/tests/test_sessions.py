"""Login sessions: the httpOnly cookie, the cross-site check, ending sessions on a password change or reset,
and shorter admin sessions."""

from datetime import datetime, timezone

import jwt

from app.core.config import settings
from app.core.deps import CSRF_HEADER, CSRF_VALUE, SESSION_COOKIE
from tests import helpers
from tests.helpers import PASSWORD

SAME_SITE = {CSRF_HEADER: CSRF_VALUE}


def test_login_sets_an_httponly_cookie_that_signs_the_browser_in(browser):
    helpers.register_parent(browser, email="ada@example.com", photo=False)
    browser.cookies.clear()
    response = browser.post("/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert browser.get("/v1/auth/me").json()["user"]["email"] == "ada@example.com"


def test_a_change_made_with_the_cookie_needs_the_same_site_header(browser):
    helpers.register_parent(browser, email="ada@example.com", photo=False)
    browser.post("/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    body = {"current_password": PASSWORD, "new_password": "a-new-password"}
    refused = browser.put("/v1/auth/me/password", json=body)  # what a hostile page could make a browser send
    assert refused.status_code == 403
    assert browser.put("/v1/auth/me/password", json=body, headers=SAME_SITE).status_code == 204


def test_logout_removes_the_cookie(browser):
    helpers.register_parent(browser, email="ada@example.com", photo=False)
    browser.post("/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    assert browser.post("/v1/auth/logout").status_code == 204
    assert browser.get("/v1/auth/me").status_code == 401


def test_changing_the_password_logs_out_every_other_device(browser):
    parent = helpers.register_parent(browser, email="ada@example.com", photo=False)  # "another device"
    browser.post("/v1/auth/login", json={"email": "ada@example.com", "password": PASSWORD})
    body = {"current_password": PASSWORD, "new_password": "a-new-password"}
    assert browser.put("/v1/auth/me/password", json=body, headers=SAME_SITE).status_code == 204

    assert browser.get("/v1/auth/me", headers=parent["headers"]).status_code == 401
    assert browser.get("/v1/auth/me").status_code == 200  # this browser got a new cookie
    assert helpers.login(browser, "ada@example.com", "a-new-password")


def test_admin_sessions_last_four_hours(client, admin_headers):
    token = admin_headers["Authorization"].split()[1]
    expires = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])["exp"]
    hours = (datetime.fromtimestamp(expires, timezone.utc) - datetime.now(timezone.utc)).total_seconds() / 3600
    assert 3.9 < hours <= 4

    parent = helpers.register_parent(client)
    token = parent["headers"]["Authorization"].split()[1]
    expires = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])["exp"]
    assert (datetime.fromtimestamp(expires, timezone.utc) - datetime.now(timezone.utc)).total_seconds() > 23 * 3600


def test_responses_carry_browser_protections(client):
    response = client.get("/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
