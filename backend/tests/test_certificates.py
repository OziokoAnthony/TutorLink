"""Spec 4 R4: certificates uploaded by the tutor and reviewed by an admin."""

import pytest
from sqlalchemy import text

from tests import helpers

WAEC = {"type": "WAEC", "institution": "Kings College Lagos", "year": "2012", "exam_number": "4250123045",
        "exam_year": "2012", "checker_pin": "123456789012"}


@pytest.fixture
def tutor(client):
    return helpers.verified_tutor(client)


def upload(client, tutor, **kwargs) -> dict:
    response = helpers.upload_certificate(client, tutor, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def steps(client, tutor) -> dict:
    return {s["key"]: s for s in client.get("/v1/onboarding", headers=tutor["headers"]).json()["steps"]}


# ---------- Uploading (R4.1, R4.2) ----------

def test_tutor_uploads_a_certificate_and_sees_it_pending(client, tutor):
    certificate = upload(client, tutor)
    assert certificate["type"] == "Degree" and certificate["institution"] == "University of Lagos"
    assert certificate["year"] == 2018 and certificate["status"] == "pending"
    assert certificate["file_name"] == "degree.pdf" and certificate["file_url"]
    assert [c["id"] for c in client.get("/v1/certificates", headers=tutor["headers"]).json()] == [certificate["id"]]
    assert client.get(certificate["file_url"].replace("http://localhost:8000", "")).content == helpers.PDF


def test_certificates_need_a_verified_nin_first(client):
    tutor = helpers.register_tutor(client)
    response = helpers.upload_certificate(client, tutor)
    assert response.status_code == 409 and "Verify your NIN" in response.json()["detail"]


@pytest.mark.parametrize("data, filename", [
    (helpers.image_bytes(fmt="PNG"), "scan.png"),
    (helpers.image_bytes(fmt="JPEG"), "scan.jpg"),
])
def test_jpg_and_png_are_accepted(client, tutor, data, filename):
    assert upload(client, tutor, data=data, filename=filename)["file_name"] == filename


@pytest.mark.parametrize("data", [helpers.image_bytes(fmt="GIF"), b"just text", b"%PD"])
def test_only_pdf_jpg_or_png(client, tutor, data):
    # Judged by the file's content, not its name.
    assert helpers.upload_certificate(client, tutor, data=data, filename="degree.pdf").status_code == 422


def test_more_than_10_mb_is_rejected(client, tutor):
    big = helpers.PDF + b"0" * (10 * 1024 * 1024)
    assert helpers.upload_certificate(client, tutor, data=big).status_code == 413


@pytest.mark.parametrize("fields", [{"type": "Diploma"}, {"institution": ""}, {"year": "2999"}, {"year": "1900"}])
def test_type_institution_and_year_are_checked(client, tutor, fields):
    assert helpers.upload_certificate(client, tutor, **fields).status_code == 422


@pytest.mark.parametrize("missing", ["exam_number", "exam_year", "checker_pin"])
def test_waec_and_neco_need_exam_number_year_and_checker_pin(client, tutor, missing):
    fields = {k: v for k, v in WAEC.items() if k != missing}
    assert helpers.upload_certificate(client, tutor, **fields).status_code == 422
    assert helpers.upload_certificate(client, tutor, **{**fields, "type": "NECO"}).status_code == 422


def test_other_types_drop_exam_details(client, tutor):
    certificate = upload(client, tutor, exam_number="123", exam_year="2010", checker_pin="999")
    assert certificate["exam_number"] is None and not certificate["has_checker_pin"]


def test_file_name_is_reduced_to_a_plain_name(client, tutor):
    certificate = upload(client, tutor, filename="C:\\Users\\me\\..\\My Degree.PDF")
    assert certificate["file_name"] == "My Degree.pdf"


# ---------- Checker PIN (R4.2) ----------

def test_checker_pin_is_unreadable_in_the_database_and_gone_after_review(client, admin_headers, db, tutor):
    certificate = upload(client, tutor, **WAEC)
    assert certificate["has_checker_pin"] and "checker_pin" not in certificate
    assert WAEC["checker_pin"] not in client.get("/v1/certificates", headers=tutor["headers"]).text
    stored = db.execute(text("SELECT * FROM certificates")).mappings().one()
    assert WAEC["checker_pin"] not in str(dict(stored)) and stored["checker_pin_encrypted"]

    queue = client.get("/v1/admin/certificates?status=pending", headers=admin_headers).json()
    assert queue[0]["checker_pin"] == WAEC["checker_pin"] and queue[0]["exam_number"] == WAEC["exam_number"]

    reviewed = helpers.review_certificate(client, admin_headers, certificate["id"]).json()
    assert reviewed["checker_pin"] is None and not reviewed["has_checker_pin"]
    db.expire_all()
    assert db.execute(text("SELECT checker_pin_encrypted FROM certificates")).scalar() is None


def test_checker_pin_is_erased_on_rejection_too(client, admin_headers, db, tutor):
    certificate = upload(client, tutor, **WAEC)
    helpers.review_certificate(client, admin_headers, certificate["id"], "rejected", "Result not found")
    assert db.execute(text("SELECT checker_pin_encrypted FROM certificates")).scalar() is None


# ---------- Who can reach the files (R4.1) ----------

def test_files_are_reachable_only_by_their_tutor_and_admins(client, admin_headers, tutor):
    certificate = upload(client, tutor)
    other = helpers.verified_tutor(client)
    parent = helpers.register_parent(client)
    assert client.get("/v1/certificates", headers=other["headers"]).json() == []
    assert client.get("/v1/certificates", headers=parent["headers"]).status_code == 403
    assert client.get("/v1/certificates").status_code == 401
    for headers in (tutor["headers"], other["headers"], parent["headers"]):
        assert client.get("/v1/admin/certificates", headers=headers).status_code == 403
    assert client.get("/v1/admin/certificates", headers=admin_headers).json()[0]["file_url"]

    url = certificate["file_url"].replace("http://localhost:8000", "")
    assert client.get(url.split("?")[0]).status_code in (403, 422)  # the link only works signed
    assert client.get(url.replace("sig=", "sig=0")).status_code == 403


# ---------- Review (R4.3) ----------

def test_admin_sees_the_certificate_next_to_the_nin_verified_name(client, admin_headers, tutor):
    upload(client, tutor)
    seen = client.get(f"/v1/admin/certificates?tutor_id={tutor['id']}", headers=admin_headers).json()[0]
    assert (seen["tutor_first_name"], seen["tutor_surname"]) == (tutor["first_name"], tutor["surname"])
    assert seen["tutor_nin_verified"] is True and seen["tutor_id"] == tutor["id"]


def test_verifying_tells_the_tutor_and_completes_the_step(client, admin_headers, tutor):
    certificate = upload(client, tutor)
    assert steps(client, tutor)["certificates"]["todo"] == ["Wait for an admin to check your certificate"]
    reviewed = helpers.review_certificate(client, admin_headers, certificate["id"], note="Checked with UNILAG")
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "verified"
    mine = client.get("/v1/certificates", headers=tutor["headers"]).json()[0]
    assert mine["status"] == "verified" and mine["review_note"] == "Checked with UNILAG" and mine["reviewed_at"]
    assert steps(client, tutor)["certificates"]["done"]
    titles = [n["title"] for n in client.get("/v1/notifications/me", headers=tutor["headers"]).json()["items"]]
    assert "Your Degree certificate is verified" in titles


def test_rejecting_needs_a_note_and_the_tutor_uploads_a_replacement(client, admin_headers, outbox, tutor):
    certificate = upload(client, tutor)
    assert helpers.review_certificate(client, admin_headers, certificate["id"], "rejected").status_code == 422
    assert helpers.review_certificate(client, admin_headers, certificate["id"], "rejected",
                                      "The scan is unreadable").status_code == 200
    assert "The scan is unreadable" in outbox[-1]["html"] and outbox[-1]["to"] == tutor["email"]
    assert steps(client, tutor)["certificates"]["todo"] == ["Upload a replacement for your rejected certificate"]

    replacement = upload(client, tutor)
    statuses = sorted(c["status"] for c in client.get("/v1/certificates", headers=tutor["headers"]).json())
    assert statuses == ["pending", "rejected"]
    helpers.review_certificate(client, admin_headers, replacement["id"])
    assert steps(client, tutor)["certificates"]["done"]


def test_a_certificate_is_reviewed_once(client, admin_headers, tutor):
    certificate = upload(client, tutor)
    helpers.review_certificate(client, admin_headers, certificate["id"])
    again = helpers.review_certificate(client, admin_headers, certificate["id"], "rejected", "Changed my mind")
    assert again.status_code == 409
    assert helpers.review_certificate(client, admin_headers, certificate["id"], "pending").status_code == 422


def test_only_admins_review(client, tutor):
    certificate = upload(client, tutor)
    assert helpers.review_certificate(client, tutor["headers"], certificate["id"]).status_code == 403


# ---------- Approval (R2.3) and badges (R4.4) ----------

def test_approving_without_a_verified_certificate_is_409(client, admin_headers, tutor):
    response = helpers.vet(client, admin_headers, tutor)
    assert response.status_code == 409 and "no verified certificate" in response.json()["detail"]
    certificate = upload(client, tutor)
    assert helpers.vet(client, admin_headers, tutor).status_code == 409  # pending isn't enough
    helpers.review_certificate(client, admin_headers, certificate["id"])
    assert helpers.vet(client, admin_headers, tutor).status_code == 200


def test_public_profile_shows_badges_but_no_files_or_numbers(client, admin_headers):
    tutor = helpers.verified_tutor(client)
    for fields in (WAEC, {}, {}):  # a WAEC and two degrees: each type is one badge
        certificate = upload(client, tutor, **fields)
        helpers.review_certificate(client, admin_headers, certificate["id"])
    rejected = upload(client, tutor, type="TRCN")
    helpers.review_certificate(client, admin_headers, rejected["id"], "rejected", "Expired")
    helpers.vet(client, admin_headers, tutor)

    public = client.get(f"/v1/tutors/{tutor['id']}")
    assert public.json()["nin_verified"] is True
    assert public.json()["verified_certificates"] == ["WAEC", "Degree"]
    for secret in ("file_url", "file_name", "certificates/", WAEC["exam_number"], "University of Lagos"):
        assert secret not in public.text
    listed = next(t for t in client.get("/v1/tutors").json() if t["user_id"] == tutor["id"])
    assert listed["verified_certificates"] == ["WAEC", "Degree"]
