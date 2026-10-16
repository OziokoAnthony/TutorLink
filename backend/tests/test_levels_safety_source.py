"""Spec 15: nursery and exam-prep levels, the guardian rule for young children, and how people heard about us."""

from uuid import UUID

import pytest

from app.domains.auth.models import User
from app.domains.bookings.service import GUARDIAN_TEXT
from tests import helpers


# ---------- R1: two new levels ----------

@pytest.mark.parametrize("level", ["nursery", "exam_prep"])
def test_tutors_offer_and_parents_book_the_new_levels(client, admin_headers, claude, level):
    tutor = helpers.approved_tutor(client, admin_headers, level=level)
    parent = helpers.register_parent(client)
    booked = helpers.book(client, parent, tutor)
    assert booked.status_code == 201, booked.text
    assert booked.json()["level"] == level
    job = client.post("/v1/jobs", headers=parent["headers"], json=helpers.job_body(level=level, guardian_present=True))
    assert job.status_code == 201, job.text
    page = client.get(f"/v1/public/levels/{level}")
    assert page.status_code == 200 and page.json()["tutors"] == 1


# ---------- R2: a parent or guardian present ----------

@pytest.mark.parametrize("level", ["nursery", "primary"])
def test_young_children_need_the_guardian_confirmation(client, admin_headers, claude, level):
    tutor = helpers.approved_tutor(client, admin_headers, level=level)
    parent = helpers.register_parent(client)
    refused = helpers.book(client, parent, tutor, guardian_present=False)
    assert refused.status_code == 422 and GUARDIAN_TEXT in refused.json()["detail"]

    booking = helpers.book(client, parent, tutor).json()
    assert booking["guardian_confirmed_at"]
    tutor_view = client.get(f"/v1/bookings/{booking['id']}", headers=tutor["headers"]).json()
    assert tutor_view["guardian_confirmed_at"] == booking["guardian_confirmed_at"]  # the tutor sees it (R2.2)

    assert client.post("/v1/jobs", headers=parent["headers"],
                       json=helpers.job_body(level=level)).status_code == 422
    job = client.post("/v1/jobs", headers=parent["headers"], json=helpers.job_body(level=level, guardian_present=True))
    assert job.status_code == 201 and job.json()["guardian_confirmed_at"]


def test_other_levels_dont_ask(client, admin_headers, claude):
    tutor = helpers.approved_tutor(client, admin_headers)  # senior secondary
    parent = helpers.register_parent(client)
    booking = helpers.book(client, parent, tutor, guardian_present=False)
    assert booking.status_code == 201 and booking.json()["guardian_confirmed_at"] is None
    job = client.post("/v1/jobs", headers=parent["headers"], json=helpers.job_body())
    assert job.status_code == 201 and job.json()["guardian_confirmed_at"] is None


# ---------- R3: how did you hear about TutorLink? ----------

def _register(client, role: str, heard_from: str | None):
    body = {"email": helpers.unique_email(role), "password": helpers.PASSWORD, "role": role,
            "heard_from": heard_from}
    body.update({"full_name": "Ada Parent"} if role == "parent" else
                {"first_name": "Tunde", "surname": "Tutor", "area": "Lekki", "offers": [helpers.offer()]})
    return client.post("/v1/auth/register", json=body)


def test_sign_up_stores_the_answer_and_admins_see_the_totals(client, db, admin_headers):
    first = _register(client, "parent", "instagram")
    assert first.status_code == 201, first.text
    assert db.get(User, UUID(first.json()["user"]["id"])).heard_from == "instagram"
    _register(client, "parent", "instagram")
    _register(client, "tutor", "friend")
    _register(client, "parent", None)
    assert _register(client, "parent", "television").status_code == 422
    google = helpers.google_register(client, "ada@gmail.com", "parent", heard_from="google")
    assert google.status_code == 201, google.text

    sources = {s["source"]: (s["parents"], s["tutors"])
               for s in client.get("/v1/admin/users/overview", headers=admin_headers).json()["heard_from"]}
    assert sources == {"instagram": (2, 0), "friend": (0, 1), "google": (1, 0), None: (1, 0)}
