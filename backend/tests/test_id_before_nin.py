"""Spec 11: tutors can start with an ID document and verify their NIN within 90 days."""

from datetime import timedelta

import pytest

from tests import helpers

NIN_MISSING = "NIN not verified, and no verified ID document"
OVERDUE = "NIN not verified within 90 days of registering"


def upload_id(client, tutor: dict, type: str = "voters_card", data: bytes = helpers.PDF, filename: str = "id.pdf"):
    return client.post("/v1/id-documents", headers=tutor["headers"], data={"type": type},
                       files={"file": (filename, data, "application/octet-stream")})


def review_id(client, admin_headers, doc_id: str, status: str = "verified", note: str | None = None):
    return client.patch(f"/v1/admin/id-documents/{doc_id}", headers=admin_headers,
                        json={"status": status, "note": note})


def steps(client, tutor) -> dict:
    return {s["key"]: s for s in client.get("/v1/onboarding", headers=tutor["headers"]).json()["steps"]}


def id_tutor(client, admin_headers) -> dict:
    """A tutor with a picture and a verified voter's card, and no NIN."""
    tutor = helpers.register_tutor(client)
    assert helpers.upload_photo(client, tutor["headers"]).status_code == 200
    doc = upload_id(client, tutor)
    assert doc.status_code == 201, doc.text
    assert review_id(client, admin_headers, doc.json()["id"]).status_code == 200
    return tutor


def approved_without_nin(client, admin_headers) -> dict:
    tutor = id_tutor(client, admin_headers)
    cert = helpers.upload_certificate(client, tutor)
    assert cert.status_code == 201, cert.text
    assert helpers.review_certificate(client, admin_headers, cert.json()["id"]).status_code == 200
    assert helpers.take_exam(client, tutor)["passed"]
    approved = helpers.vet(client, admin_headers, tutor)
    assert approved.status_code == 200, approved.text
    return tutor


def titles(client, user) -> list[str]:
    return [n["title"] for n in client.get("/v1/notifications/me", headers=user["headers"]).json()["items"]]


# ---------- R1: ID documents ----------

@pytest.mark.parametrize("type", ["nin", "voters_card", "drivers_licence", "passport"])
def test_each_kind_of_id_can_be_uploaded(client, type):
    tutor = helpers.register_tutor(client)
    response = upload_id(client, tutor, type)
    assert response.status_code == 201, response.text
    assert response.json()["type"] == type and response.json()["status"] == "pending"
    assert response.json()["file_url"]


def test_ids_are_files_only_admins_and_the_tutor_see(client, admin_headers):
    tutor = helpers.register_tutor(client)
    assert upload_id(client, tutor, data=b"not a document", filename="id.txt").status_code == 422
    doc = upload_id(client, tutor).json()
    other = helpers.register_tutor(client)
    assert client.get("/v1/id-documents", headers=other["headers"]).json() == []
    parent = helpers.register_parent(client)
    assert upload_id(client, parent).status_code == 403
    assert client.get("/v1/admin/id-documents", headers=tutor["headers"]).status_code == 403
    queue = client.get("/v1/admin/id-documents", headers=admin_headers, params={"status": "pending"}).json()
    assert [d["id"] for d in queue] == [doc["id"]] and queue[0]["tutor_surname"] == "Tutor"


def test_a_rejected_id_is_explained_and_can_be_replaced(client, admin_headers):
    tutor = helpers.register_tutor(client)
    doc = upload_id(client, tutor).json()
    assert upload_id(client, tutor, "passport").status_code == 409  # one waiting at a time (R1.3)
    assert review_id(client, admin_headers, doc["id"], "rejected").status_code == 422  # a note is needed
    rejected = review_id(client, admin_headers, doc["id"], "rejected", "The picture is too blurry to read.")
    assert rejected.status_code == 200
    assert "Your voter's card wasn't accepted" in titles(client, tutor)
    assert review_id(client, admin_headers, doc["id"]).status_code == 409  # already reviewed
    assert upload_id(client, tutor, "passport").status_code == 201


# ---------- R2: identity in onboarding ----------

def test_a_verified_id_counts_as_identity_and_a_pending_one_opens_certificates(client, admin_headers, claude):
    tutor = helpers.register_tutor(client)
    assert helpers.upload_photo(client, tutor["headers"]).status_code == 200
    assert helpers.upload_certificate(client, tutor).status_code == 409  # neither NIN nor ID yet
    doc = upload_id(client, tutor).json()
    assert steps(client, tutor)["nin"]["done"] is False
    cert = helpers.upload_certificate(client, tutor)
    assert cert.status_code == 201  # a pending ID opens certificates (R2.2)
    helpers.review_certificate(client, admin_headers, cert.json()["id"])
    assert helpers.take_exam(client, tutor)["passed"]

    refused = helpers.vet(client, admin_headers, tutor)
    assert refused.status_code == 409 and NIN_MISSING in refused.json()["detail"]
    review_id(client, admin_headers, doc["id"])
    assert steps(client, tutor)["nin"]["done"] is True
    onboarding = client.get("/v1/onboarding", headers=tutor["headers"]).json()
    assert onboarding["nin_verified"] is False and onboarding["nin_due_at"]
    assert helpers.vet(client, admin_headers, tutor).status_code == 200  # R2.3


# ---------- R3: the 90-day deadline ----------

def test_an_approved_tutor_without_a_nin_is_hidden_after_90_days_until_they_verify(client, admin_headers, claude, clock):
    tutor = approved_without_nin(client, admin_headers)
    parent = helpers.register_parent(client)
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=parent["headers"]).status_code == 200
    assert tutor["id"] in [t["user_id"] for t in client.get("/v1/tutors", headers=parent["headers"]).json()]

    clock.travel(days=90, minutes=1)
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=parent["headers"]).status_code == 404
    assert tutor["id"] not in [t["user_id"] for t in client.get("/v1/tutors", headers=parent["headers"]).json()]
    assert helpers.book(client, parent, tutor).status_code == 404
    assert client.get("/v1/jobs", headers=tutor["headers"]).status_code == 403
    assert client.get("/v1/onboarding", headers=tutor["headers"]).json()["nin_overdue"] is True

    tutor["nin"] = helpers.dojah.add(tutor["first_name"], tutor["surname"])
    assert helpers.check_nin(client, tutor, tutor["nin"]).json()["verified"]
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=parent["headers"]).status_code == 200  # R3.4


def test_an_overdue_tutor_cant_be_approved(client, admin_headers, claude, clock):
    tutor = id_tutor(client, admin_headers)
    cert = helpers.upload_certificate(client, tutor).json()
    helpers.review_certificate(client, admin_headers, cert["id"])
    assert helpers.take_exam(client, tutor)["passed"]
    clock.travel(days=91)
    refused = helpers.vet(client, admin_headers, tutor)
    assert refused.status_code == 409 and OVERDUE in refused.json()["detail"]


def test_a_booking_requested_before_the_deadline_carries_on(client, admin_headers, claude, clock, paystack):
    tutor = approved_without_nin(client, admin_headers)
    parent = helpers.register_parent(client)
    clock.travel(days=89, hours=12)
    booking = helpers.requested_booking(client, parent, tutor, start_date=helpers.wat_today(clock.now()) + timedelta(days=3))
    clock.travel(days=1)  # past the deadline
    accepted = client.post(f"/v1/bookings/{booking['id']}/accept", headers=tutor["headers"])
    assert accepted.status_code == 200, accepted.text
    due = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["periods"][0]["amount"]
    assert helpers.deposit(client, paystack, parent, due).status_code == 200
    paid = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()
    assert paid["status"] == "active", paid
    assert [l for l in helpers.lessons(client, parent) if l["booking_id"] == booking["id"]]  # lessons created


def test_reminders_go_out_once_at_30_7_and_1_days_and_when_it_passes(client, db, admin_headers, clock):
    tutor = helpers.register_tutor(client)
    nin_tutor = helpers.verified_tutor(client)
    start, expected = clock.now(), []
    for days, title in ((61, "Verify your NIN within 30 days"), (84, "Verify your NIN within 7 days"),
                        (89.5, "Verify your NIN within 1 day"), (91, "Parents can no longer see your profile")):
        clock.set(start + timedelta(days=days))
        helpers.run_jobs(db, clock)
        helpers.run_jobs(db, clock)  # each is sent once
        expected.append(title)
        assert sorted(t for t in titles(client, tutor) if "NIN" in t or "profile" in t) == sorted(expected)
    assert not [t for t in titles(client, nin_tutor) if "Verify your NIN" in t]


# ---------- R4: admins ----------

def test_reviewing_an_id_is_logged_and_overdue_tutors_are_marked(client, admin_headers, clock):
    tutor = helpers.register_tutor(client, full_name="Tunde Bello")
    doc = upload_id(client, tutor).json()
    review_id(client, admin_headers, doc["id"])
    texts = [e["text"] for e in client.get("/v1/admin/dashboard", headers=admin_headers).json()["recent"]]
    assert "Verified the voter's card of tutor Tunde Bello" in texts
    clock.travel(days=91)
    row = next(r for r in client.get("/v1/admin/users", headers=admin_headers, params={"role": "tutor"}).json()
               if r["id"] == tutor["id"])
    assert row["nin_overdue"] is True
