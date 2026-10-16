"""Spec 9: parents and tutors agree to their own privacy notice, terms and disclaimer."""

from sqlmodel import select

from app.domains.content.models import LegalAcceptance
from tests import helpers

TEXT = "## Who we are\n\nTutorLink connects parents with tutors. " + "This is the body of the document. " * 5
KINDS = ("privacy", "terms", "disclaimer")
MUST_AGREE = "Please read and agree to TutorLink's terms to continue."


def publish(client, admin_headers, audience: str, kinds=KINDS, text: str = TEXT):
    for kind in kinds:
        response = client.post(f"/v1/admin/legal/{audience}/{kind}", headers=admin_headers,
                               json={"body": f"{text} ({audience} {kind})"})
        assert response.status_code == 201, response.text


def mine(client, user) -> dict:
    response = client.get("/v1/legal/me", headers=user["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def agree(client, user, ids=None):
    ids = ids if ids is not None else [d["id"] for d in mine(client, user)["documents"]]
    return client.post("/v1/legal/me/accept", headers=user["headers"], json={"document_ids": ids})


def blocked(response) -> bool:
    return response.status_code == 403 and response.json()["detail"] == MUST_AGREE


# ---------- R1: documents per role ----------

def test_parents_and_tutors_have_their_own_documents(client, admin_headers):
    publish(client, admin_headers, "parent")
    publish(client, admin_headers, "tutor")
    assert client.get("/v1/legal/terms").json()["body"].endswith("(parent terms)")  # parents' by default (R1.3)
    assert client.get("/v1/legal/terms", params={"audience": "tutor"}).json()["body"].endswith("(tutor terms)")

    parent, tutor = helpers.register_parent(client, photo=False), helpers.register_tutor(client)
    assert {d["audience"] for d in mine(client, parent)["documents"]} == {"parent"}
    assert [d["kind"] for d in mine(client, tutor)["documents"]] == list(KINDS)

    versions = client.get("/v1/admin/legal/tutor/terms", headers=admin_headers).json()
    assert len(versions) == 1 and versions[0]["audience"] == "tutor"


# ---------- R2, R3: parents ----------

def test_a_new_parent_must_agree_before_doing_anything_else(client, admin_headers):
    publish(client, admin_headers, "parent")
    parent = helpers.register_parent(client, photo=False)
    assert mine(client, parent)["required"] is True

    assert blocked(client.post("/v1/jobs", headers=parent["headers"], json=helpers.job_body()))
    assert blocked(client.get("/v1/wallet/me", headers=parent["headers"]))
    for method, path in (("GET", "/v1/auth/me"), ("GET", "/v1/notifications/me"), ("GET", "/v1/legal/me")):
        assert client.request(method, path, headers=parent["headers"]).status_code == 200, path

    agreed = agree(client, parent)
    assert agreed.status_code == 200 and agreed.json()["required"] is False
    assert all(d["accepted_at"] for d in agreed.json()["documents"])
    assert client.get("/v1/wallet/me", headers=parent["headers"]).status_code == 200
    assert client.post("/v1/auth/logout", headers=parent["headers"]).status_code == 204


def test_a_parent_signed_up_with_google_must_agree_too(client, admin_headers):
    publish(client, admin_headers, "parent")
    response = helpers.google_register(client, "ada@gmail.com", "parent")
    assert response.status_code == 201, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert blocked(client.get("/v1/wallet/me", headers=headers))
    assert mine(client, {"headers": headers})["required"] is True


def test_each_agreement_is_stored_with_the_version_and_ip(client, db, admin_headers):
    publish(client, admin_headers, "parent")
    parent = helpers.register_parent(client, photo=False)
    ids = [d["id"] for d in mine(client, parent)["documents"]]
    assert agree(client, parent).status_code == 200
    assert agree(client, parent).status_code == 200  # agreeing twice stores nothing new
    rows = db.exec(select(LegalAcceptance).where(LegalAcceptance.user_id == parent["id"])).all()
    assert sorted(str(r.document_id) for r in rows) == sorted(ids)
    assert all(r.ip for r in rows)


def test_only_the_latest_versions_can_be_agreed_to(client, admin_headers):
    publish(client, admin_headers, "parent")
    parent = helpers.register_parent(client, photo=False)
    old = [d["id"] for d in mine(client, parent)["documents"]]
    publish(client, admin_headers, "parent", kinds=("terms",), text=TEXT + " New.")
    assert agree(client, parent, old).status_code == 409  # someone published meanwhile (R2.3)
    assert agree(client, parent, old[:2]).status_code == 409  # all three at once (R2.1)
    assert agree(client, parent).status_code == 200


# ---------- R4: tutors ----------

def test_a_tutor_agrees_as_the_last_onboarding_step_before_approval(client, admin_headers, claude):
    publish(client, admin_headers, "tutor")
    tutor = helpers.register_tutor(client)
    assert mine(client, tutor)["required"] is False  # onboarding goes on as before (R4.3)
    assert mine(client, tutor)["can_accept"] is False
    assert agree(client, tutor).status_code == 409  # other steps first (R4.1)
    assert client.get("/v1/onboarding", headers=tutor["headers"]).status_code == 200

    tutor = helpers.ready_tutor(client, admin_headers)
    steps = {s["key"]: s for s in client.get("/v1/onboarding", headers=tutor["headers"]).json()["steps"]}
    assert steps["agreement"]["done"] is False and "terms not agreed" in steps["review"]["todo"]
    refused = helpers.vet(client, admin_headers, tutor)
    assert refused.status_code == 409 and "terms not agreed" in refused.json()["detail"]  # R4.2

    assert mine(client, tutor)["can_accept"] is True
    assert agree(client, tutor).status_code == 200
    assert helpers.vet(client, admin_headers, tutor).status_code == 200


# ---------- R5: new versions ----------

def test_a_new_version_must_be_agreed_to_by_its_audience_only(client, admin_headers, claude):
    publish(client, admin_headers, "parent")
    publish(client, admin_headers, "tutor")
    parent = helpers.register_parent(client, photo=False)
    agree(client, parent)
    tutor = helpers.ready_tutor(client, admin_headers)
    agree(client, tutor)
    assert helpers.vet(client, admin_headers, tutor).status_code == 200

    publish(client, admin_headers, "parent", kinds=("terms",), text=TEXT + " New.")
    assert blocked(client.get("/v1/wallet/me", headers=parent["headers"]))
    assert client.get("/v1/earnings/me", headers=tutor["headers"]).status_code != 403  # not a tutor document

    publish(client, admin_headers, "tutor", kinds=("privacy",), text=TEXT + " New.")
    assert blocked(client.get("/v1/onboarding", headers=tutor["headers"]))  # agreed before: held back (R5.2)
    assert agree(client, tutor).status_code == 200
    assert client.get("/v1/onboarding", headers=tutor["headers"]).status_code == 200


def test_an_approved_tutor_who_never_agreed_must_agree(client, admin_headers, claude):
    """R5.3: at go-live, approved tutors agree on their next visit."""
    tutor = helpers.approved_tutor(client, admin_headers)  # approved before any document existed
    publish(client, admin_headers, "tutor")
    assert blocked(client.get("/v1/onboarding", headers=tutor["headers"]))
    assert agree(client, tutor).status_code == 200


# ---------- R6: admins ----------

def test_admins_never_agree(client, admin_headers):
    publish(client, admin_headers, "parent")
    publish(client, admin_headers, "tutor")
    assert client.get("/v1/admin/dashboard", headers=admin_headers).status_code == 200
    assert client.get("/v1/legal/me", headers=admin_headers).status_code == 403
    texts = [e["text"] for e in client.get("/v1/admin/dashboard", headers=admin_headers).json()["recent"]]
    assert "Published a new version of the tutors' terms of service" in texts
