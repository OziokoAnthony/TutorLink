from tests import helpers


def listed_ids(client, **params) -> set[str]:
    response = client.get("/v1/tutors", params=params)
    assert response.status_code == 200
    return {t["user_id"] for t in response.json()}


def test_unapproved_tutor_not_in_list(client):
    tutor = helpers.register_tutor(client)
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


def test_filters_match_any_offer_by_subject_level_and_area(client, admin_headers):
    sciences = helpers.approved_tutor(client, admin_headers, area="Lekki Phase 1",
                                      subjects=["Mathematics", "Physics"])
    english = helpers.approved_tutor(client, admin_headers, area="Surulere", subjects=["English"], level="primary")

    assert listed_ids(client, subject="physics") == {sciences["id"]}
    assert listed_ids(client, subject="mathematics") == {sciences["id"]}
    assert listed_ids(client, level="primary") == {english["id"]}
    assert listed_ids(client, area="lekki") == {sciences["id"]}
    assert listed_ids(client, subject="English", level="senior_secondary") == set()


def test_listing_shows_offers_and_lowest_price_and_sorts_by_price(client, admin_headers):
    dear = helpers.approved_tutor(client, admin_headers, price="9000.00")
    cheap = helpers.approved_tutor(client, admin_headers, offers=[
        helpers.offer(price="7000.00"), helpers.offer(subjects=["Chemistry"], price="4000.00"),
    ])
    listing = client.get("/v1/tutors", params={"sort": "price"}).json()
    assert [t["user_id"] for t in listing] == [cheap["id"], dear["id"]]
    assert listing[0]["price_from"] == "4000.00"
    assert len(listing[0]["offers"]) == 2


def test_pagination(client, admin_headers):
    for _ in range(3):
        helpers.approved_tutor(client, admin_headers)
    assert len(client.get("/v1/tutors", params={"limit": 2}).json()) == 2
    assert len(client.get("/v1/tutors", params={"skip": 2, "limit": 2}).json()) == 1


def test_public_listing_hides_contact_and_vetting_details(client, admin_headers):
    helpers.approved_tutor(client, admin_headers)
    tutor = client.get("/v1/tutors").json()[0]
    assert "phone" not in tutor and "vetting_note" not in tutor
    assert tutor["offers"][0]["subjects"] == ["Mathematics"]


def test_tutor_updates_profile(client):
    tutor = helpers.register_tutor(client)
    response = client.post("/v1/tutors/profile", headers=tutor["headers"], json={
        "first_name": "Tunde", "surname": "Updated", "area": "Ikeja", "bio": "10 years",
    })
    assert response.status_code == 200
    assert response.json()["full_name"] == "Tunde Updated"


def test_profile_endpoints_are_tutor_only(client):
    parent = helpers.register_parent(client)
    assert client.post("/v1/tutors/profile", headers=parent["headers"],
                       json={"first_name": "X", "surname": "Z", "area": "Y"}).status_code == 403
    assert client.post("/v1/tutors/profile/offers", headers=parent["headers"], json=helpers.offer()).status_code == 403


def test_tutor_adds_edits_and_removes_offers(client):
    tutor = helpers.register_tutor(client)
    created = client.post("/v1/tutors/profile/offers", headers=tutor["headers"], json=helpers.offer(
        subjects=["English", " english ", "Literature"], level="junior_secondary", price="3000.00",
        windows=[{"day_of_week": 5, "start_time": "10:00", "end_time": "12:00"}],
    ))
    assert created.status_code == 201
    assert created.json()["subjects"] == ["English", "Literature"]  # duplicates dropped

    edited = client.put(f"/v1/tutors/profile/offers/{created.json()['id']}", headers=tutor["headers"],
                        json=helpers.offer(subjects=["English"], price="3500.00"))
    assert edited.status_code == 200
    assert edited.json()["price"] == "3500.00" and edited.json()["subjects"] == ["English"]

    assert client.delete(f"/v1/tutors/profile/offers/{created.json()['id']}", headers=tutor["headers"]).status_code == 204
    assert len(client.get("/v1/tutors/profile/offers", headers=tutor["headers"]).json()) == 1


def test_last_offer_cannot_be_removed(client):
    tutor = helpers.register_tutor(client)
    assert client.delete(f"/v1/tutors/profile/offers/{tutor['offer_id']}", headers=tutor["headers"]).status_code == 409


def test_cannot_change_another_tutors_offer(client):
    tutor = helpers.register_tutor(client)
    other = helpers.register_tutor(client)
    url = f"/v1/tutors/profile/offers/{tutor['offer_id']}"
    assert client.put(url, headers=other["headers"], json=helpers.offer()).status_code == 403
    assert client.delete(url, headers=other["headers"]).status_code == 403


def test_offer_window_must_end_after_it_starts(client):
    tutor = helpers.register_tutor(client)
    response = client.post("/v1/tutors/profile/offers", headers=tutor["headers"], json=helpers.offer(
        windows=[{"day_of_week": 1, "start_time": "12:00", "end_time": "11:00"}]))
    assert response.status_code == 422
