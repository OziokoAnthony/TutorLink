"""Spec 8: admin names, the welcome, sessions and the activity log."""

from sqlmodel import select

from app.domains.activity.models import AdminActivity
from tests import helpers

TEMPORARY = "temporary-pass-1"


def _dashboard(client, headers) -> dict:
    response = client.get("/v1/admin/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _texts(entries: list[dict]) -> list[str]:
    return [e["text"] for e in entries]


def _add_admin(client, super_headers, name: str = "Ada Obi") -> dict:
    email = helpers.unique_email("admin")
    response = client.post("/v1/admin/admins", headers=super_headers,
                           json={"name": name, "email": email, "password": TEMPORARY})
    assert response.status_code == 201, response.text
    return {"id": response.json()["id"], "email": email, "headers": helpers.login(client, email, TEMPORARY)}


def _add_subject(client, headers, name: str):
    return client.post("/v1/admin/subjects", headers=headers, json={"name": name, "group": "international"})


# ---------- R1: names ----------

def test_admins_are_greeted_by_the_name_they_were_given_and_can_change_it(client, admin_headers):
    super_dash = _dashboard(client, admin_headers)
    assert super_dash["name"] is None and super_dash["email"]  # made before spec 8: greeted by email (R1.3)
    assert super_dash["is_super_admin"] is True

    ada = _add_admin(client, admin_headers, name="  Ada   Obi ")
    assert _dashboard(client, ada["headers"])["name"] == "Ada Obi"
    assert client.put("/v1/admin/me/name", headers=ada["headers"], json={"name": "Ada Okafor"}).status_code == 200
    assert _dashboard(client, ada["headers"])["name"] == "Ada Okafor"
    assert client.put("/v1/admin/me/name", headers=ada["headers"], json={"name": " a "}).status_code == 422

    listed = {a["id"]: a for a in client.get("/v1/admin/admins", headers=admin_headers).json()}
    assert listed[ada["id"]]["name"] == "Ada Okafor"


def test_an_admin_needs_a_name(client, admin_headers):
    response = client.post("/v1/admin/admins", headers=admin_headers,
                           json={"email": helpers.unique_email("admin"), "password": TEMPORARY})
    assert response.status_code == 422


# ---------- R2: the log ----------

def test_each_action_writes_one_line_naming_the_item(client, admin_headers):
    ada = _add_admin(client, admin_headers)
    assert _add_subject(client, ada["headers"], "Data Science").status_code == 201
    subject_id = next(s["id"] for s in client.get("/v1/admin/subjects", headers=ada["headers"]).json()
                      if s["name"] == "Data Science")
    client.patch(f"/v1/admin/subjects/{subject_id}", headers=ada["headers"], json={"is_offered": False})
    client.patch(f"/v1/admin/subjects/{subject_id}", headers=ada["headers"], json={"is_offered": True})
    assert client.put("/v1/admin/fees", headers=ada["headers"],
                      json={"parent_fee_rate": "0.08", "tutor_fee_rate": "0.125"}).status_code == 200
    client.put("/v1/auth/me/password", headers=ada["headers"],
               json={"current_password": TEMPORARY, "new_password": "ada-own-password"})

    assert _texts(_dashboard(client, helpers.login(client, ada["email"], "ada-own-password"))["recent"]) == [
        "Changed password",
        "Changed the fees: parents 8%, tutors 12.5%",
        "Restored subject Data Science",
        "Removed subject Data Science",
        "Added subject Data Science",
    ]
    assert _texts(_dashboard(client, admin_headers)["recent"])[0].startswith("Added admin Ada Obi (")


def test_a_refused_action_writes_nothing(client, admin_headers):
    ada = _add_admin(client, admin_headers)
    assert _add_subject(client, ada["headers"], "Data Science").status_code == 201
    assert _add_subject(client, ada["headers"], "data science").status_code == 409
    assert _add_subject(client, ada["headers"], "<b>").status_code == 422
    assert client.post("/v1/admin/admins", headers=ada["headers"],  # not the super admin: 403
                       json={"name": "Eve", "email": helpers.unique_email("x"), "password": TEMPORARY}).status_code == 403
    assert client.patch("/v1/tutors/00000000-0000-0000-0000-000000000000/vet", headers=ada["headers"],
                        json={"status": "approved"}).status_code == 404
    assert _texts(_dashboard(client, ada["headers"])["recent"]) == ["Added subject Data Science"]


def test_parents_and_tutors_leave_no_activity(client, db):
    parent = helpers.register_parent(client)
    helpers.login(client, parent["email"])
    assert client.get("/v1/admin/dashboard", headers=parent["headers"]).status_code == 403
    assert db.exec(select(AdminActivity)).all() == []


# ---------- R3: sessions ----------

def test_last_session_is_the_one_before_this_login(client, admin_headers):
    ada = _add_admin(client, admin_headers)
    first = _dashboard(client, ada["headers"])
    assert first["last_session"] is None and first["session_started_at"]  # first login (R3.2)

    _add_subject(client, ada["headers"], "Data Science")
    _add_subject(client, ada["headers"], "Robotics")
    again = _dashboard(client, helpers.login(client, ada["email"], TEMPORARY))
    last = again["last_session"]
    assert last["started_at"] == first["session_started_at"] and last["ended_at"] == again["session_started_at"]
    assert _texts(last["actions"]) == ["Added subject Robotics", "Added subject Data Science"]

    third = _dashboard(client, helpers.login(client, ada["email"], TEMPORARY))
    assert third["last_session"]["actions"] == []  # nothing changed in the second session


# ---------- R4: who sees what ----------

def test_the_super_admin_sees_the_team_and_can_filter_by_admin(client, admin_headers):
    ada = _add_admin(client, admin_headers, name="Ada Obi")
    bayo = _add_admin(client, admin_headers, name="Bayo Ade")
    _add_subject(client, ada["headers"], "Data Science")
    _add_subject(client, bayo["headers"], "Robotics")
    _add_subject(client, admin_headers, "Astronomy")

    team = client.get("/v1/admin/activity", headers=admin_headers).json()
    assert [(e["admin_name"], e["text"]) for e in team] == [("Bayo Ade", "Added subject Robotics"),
                                                           ("Ada Obi", "Added subject Data Science")]
    only_ada = client.get("/v1/admin/activity", params={"admin_id": ada["id"]}, headers=admin_headers).json()
    assert _texts(only_ada) == ["Added subject Data Science"]


def test_an_ordinary_admin_sees_only_their_own_activity(client, admin_headers):
    super_id = client.get("/v1/auth/me", headers=admin_headers).json()["user"]["id"]
    ada = _add_admin(client, admin_headers)
    bayo = _add_admin(client, admin_headers)
    _add_subject(client, admin_headers, "Astronomy")
    _add_subject(client, bayo["headers"], "Robotics")

    assert client.get("/v1/admin/activity", headers=ada["headers"]).status_code == 403
    assert client.get("/v1/admin/activity", params={"admin_id": super_id}, headers=ada["headers"]).status_code == 403
    dash = _dashboard(client, ada["headers"])
    assert dash["recent"] == [] and dash["is_super_admin"] is False
    for text in ("Astronomy", "Robotics", "Added admin"):
        assert text not in str(dash)
