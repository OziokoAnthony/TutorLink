"""Admins add and remove each other from /admin; the first admin comes from app.scripts.create_admin."""

from tests import helpers

TEMPORARY = "temporary-pass-1"


def _add(client, admin_headers, email: str, password: str = TEMPORARY, name: str = "Ada Admin"):
    return client.post("/v1/admin/admins", headers=admin_headers,
                       json={"name": name, "email": email, "password": password})


def _me(client, headers) -> dict:
    return client.get("/v1/auth/me", headers=headers).json()["user"]


def test_an_admin_adds_another_who_logs_in_and_changes_the_temporary_password(client, admin_headers):
    email = helpers.unique_email("new-admin")
    added = _add(client, admin_headers, f"  {email.upper()} ")
    assert added.status_code == 201, added.text
    assert added.json()["email"] == email and added.json()["is_active"] is True
    assert "password_hash" not in added.json()

    headers = helpers.login(client, email, TEMPORARY)
    assert _me(client, headers)["role"] == "admin"
    assert email in [a["email"] for a in client.get("/v1/admin/admins", headers=headers).json()]

    changed = client.put("/v1/auth/me/password", headers=headers,
                         json={"current_password": TEMPORARY, "new_password": "my-own-password"})
    assert changed.status_code == 204
    helpers.login(client, email, "my-own-password")
    assert client.post("/v1/auth/login", json={"email": email, "password": TEMPORARY}).status_code == 401


def test_an_email_already_in_use_or_a_short_password_is_refused(client, admin_headers):
    parent = helpers.register_parent(client)
    assert _add(client, admin_headers, parent["email"]).status_code == 409
    email = helpers.unique_email("admin")
    assert _add(client, admin_headers, email).status_code == 201
    assert _add(client, admin_headers, email).status_code == 409
    assert _add(client, admin_headers, helpers.unique_email("admin"), "short").status_code == 422


def test_only_admins_see_add_and_remove_admins(client, admin_headers):
    parent = helpers.register_parent(client)
    tutor = helpers.register_tutor(client)
    some_admin = _me(client, admin_headers)["id"]
    for headers in (parent["headers"], tutor["headers"]):
        assert client.get("/v1/admin/admins", headers=headers).status_code == 403
        assert _add(client, headers, helpers.unique_email("x")).status_code == 403
        assert client.delete(f"/v1/admin/admins/{some_admin}", headers=headers).status_code == 403
    assert client.get("/v1/admin/admins").status_code == 401


def test_a_removed_admin_is_logged_out_and_can_be_brought_back_with_a_new_password(client, admin_headers):
    email = helpers.unique_email("admin")
    admin_id = _add(client, admin_headers, email).json()["id"]
    their_headers = helpers.login(client, email, TEMPORARY)

    assert client.delete(f"/v1/admin/admins/{admin_id}", headers=admin_headers).status_code == 204
    assert client.get("/v1/auth/me", headers=their_headers).status_code == 401
    assert client.post("/v1/auth/login", json={"email": email, "password": TEMPORARY}).status_code == 401
    listed = {a["id"]: a for a in client.get("/v1/admin/admins", headers=admin_headers).json()}
    assert listed[admin_id]["is_active"] is False

    back = _add(client, admin_headers, email, "a-fresh-password")
    assert back.status_code == 201 and back.json()["id"] == admin_id and back.json()["is_active"] is True
    assert client.get("/v1/auth/me", headers=their_headers).status_code == 401  # old sessions stay ended
    assert client.post("/v1/auth/login", json={"email": email, "password": TEMPORARY}).status_code == 401
    helpers.login(client, email, "a-fresh-password")


def test_the_first_admin_is_the_only_super_admin(client, db, admin_headers):
    """admin_headers is the first admin of each (truncated) test database."""
    second = helpers.create_admin(client, db)
    listed = {a["id"]: a for a in client.get("/v1/admin/admins", headers=admin_headers).json()}
    assert listed[_me(client, admin_headers)["id"]]["is_super_admin"] is True
    assert listed[_me(client, second)["id"]]["is_super_admin"] is False
    added = _add(client, admin_headers, helpers.unique_email("admin"))
    assert added.json()["is_super_admin"] is False


def test_the_super_admin_cant_be_removed_and_other_admins_cant_add_or_remove(client, admin_headers):
    super_id = _me(client, admin_headers)["id"]
    refused = client.delete(f"/v1/admin/admins/{super_id}", headers=admin_headers)
    assert refused.status_code == 409 and "super admin" in refused.json()["detail"]
    assert client.get("/v1/auth/me", headers=admin_headers).status_code == 200

    emails = [helpers.unique_email("admin") for _ in range(2)]
    ids = [_add(client, admin_headers, email).json()["id"] for email in emails]
    other = helpers.login(client, emails[0], TEMPORARY)
    assert client.get("/v1/admin/admins", headers=other).status_code == 200  # they can see who the admins are
    for response in (_add(client, other, helpers.unique_email("admin")),
                     client.delete(f"/v1/admin/admins/{ids[1]}", headers=other),
                     client.delete(f"/v1/admin/admins/{super_id}", headers=other)):
        assert response.status_code == 403 and "super admin" in response.json()["detail"]
    assert all(a["is_active"] for a in client.get("/v1/admin/admins", headers=admin_headers).json())


def test_nobody_removes_a_non_admin(client, admin_headers):
    parent = helpers.register_parent(client)
    assert client.delete(f"/v1/admin/admins/{parent['id']}", headers=admin_headers).status_code == 404
    assert client.get("/v1/auth/me", headers=parent["headers"]).status_code == 200
