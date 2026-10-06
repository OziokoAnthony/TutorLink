from tests import helpers


def listed_ids(client, **params) -> set[str]:
    response = client.get("/v1/tutors", params=params)
    assert response.status_code == 200
    return {t["user_id"] for t in response.json()}


def test_unapproved_tutor_not_in_list(client):
    tutor = helpers.register_tutor(client)
    helpers.add_subject(client, tutor)
    assert tutor["id"] not in listed_ids(client)
    assert client.get(f"/v1/tutors/{tutor['id']}").status_code == 404


def test_admin_approves_then_tutor_appears(client, admin_headers):
    tutor = helpers.register_tutor(client)
    response = helpers.vet(client, admin_headers, tutor, "approved")
    assert response.status_code == 200
    assert response.json()["vetting_status"] == "approved"
    assert tutor["id"] in listed_ids(client)
    assert client.get(f"/v1/tutors/{tutor['id']}").status_code == 200


def test_admin_rejects_tutor_stays_hidden_with_note(client, admin_headers):
    tutor = helpers.register_tutor(client)
    response = helpers.vet(client, admin_headers, tutor, "rejected", note="Certificates unclear")
    assert response.status_code == 200
    assert response.json()["vetting_status"] == "rejected"
    assert response.json()["vetting_note"] == "Certificates unclear"
    assert tutor["id"] not in listed_ids(client)


def test_non_admin_cannot_vet(client):
    tutor = helpers.register_tutor(client)
    parent = helpers.register_parent(client)
    assert helpers.vet(client, parent["headers"], tutor).status_code == 403
    assert helpers.vet(client, tutor["headers"], tutor).status_code == 403


def test_pending_list_is_admin_only_and_shows_pending(client, admin_headers):
    pending = helpers.register_tutor(client)
    approved = helpers.approved_tutor(client, admin_headers)
    response = client.get("/v1/admin/tutors/pending", headers=admin_headers)
    assert response.status_code == 200
    ids = {t["user_id"] for t in response.json()}
    assert pending["id"] in ids and approved["id"] not in ids
    assert client.get("/v1/admin/tutors/pending", headers=pending["headers"]).status_code == 403


def test_filters_by_subject_level_and_area(client, admin_headers):
    maths = helpers.approved_tutor(client, admin_headers, area="Lekki Phase 1")
    english = helpers.register_tutor(client, area="Surulere")
    helpers.add_subject(client, english, subject="English", level="primary")
    helpers.vet(client, admin_headers, english)

    assert listed_ids(client, subject="mathematics") == {maths["id"]}
    assert listed_ids(client, level="primary") == {english["id"]}
    assert listed_ids(client, area="lekki") == {maths["id"]}
    assert listed_ids(client, subject="English", level="senior_secondary") == set()


def test_pagination(client, admin_headers):
    for _ in range(3):
        helpers.approved_tutor(client, admin_headers)
    assert len(client.get("/v1/tutors", params={"limit": 2}).json()) == 2
    assert len(client.get("/v1/tutors", params={"skip": 2, "limit": 2}).json()) == 1


def test_public_listing_hides_contact_and_vetting_details(client, admin_headers):
    helpers.approved_tutor(client, admin_headers)
    tutor = client.get("/v1/tutors").json()[0]
    assert "phone" not in tutor and "vetting_note" not in tutor
    assert tutor["subjects"][0]["subject"] == "Mathematics"


def test_tutor_updates_profile(client):
    tutor = helpers.register_tutor(client)
    response = client.post("/v1/tutors/profile", headers=tutor["headers"], json={
        "full_name": "Tunde Updated", "area": "Ikeja", "rate_per_session": "6000.00", "bio": "10 years",
    })
    assert response.status_code == 200
    assert response.json()["full_name"] == "Tunde Updated"
    assert response.json()["rate_per_session"] == "6000.00"


def test_profile_endpoints_are_tutor_only(client):
    parent = helpers.register_parent(client)
    response = client.post("/v1/tutors/profile", headers=parent["headers"], json={
        "full_name": "X", "area": "Y", "rate_per_session": "1000",
    })
    assert response.status_code == 403


def test_duplicate_subject_is_409(client):
    tutor = helpers.register_tutor(client)
    helpers.add_subject(client, tutor)
    response = client.post("/v1/tutors/profile/subjects", headers=tutor["headers"],
                           json={"subject": " mathematics ", "level": "senior_secondary"})
    assert response.status_code == 409


def test_remove_own_subject_but_not_others(client):
    tutor = helpers.register_tutor(client)
    other = helpers.register_tutor(client)
    subject = helpers.add_subject(client, tutor)
    assert client.delete(f"/v1/tutors/profile/subjects/{subject['id']}", headers=other["headers"]).status_code == 403
    assert client.delete(f"/v1/tutors/profile/subjects/{subject['id']}", headers=tutor["headers"]).status_code == 204
    assert client.delete(f"/v1/tutors/profile/subjects/{subject['id']}", headers=tutor["headers"]).status_code == 404
