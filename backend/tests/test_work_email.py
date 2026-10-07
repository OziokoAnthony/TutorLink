"""Tutors are assigned a work email (initial of surname + first name) and log in with it only."""

from app.domains.auth.work_email import local_part
from tests import helpers
from tests.helpers import PASSWORD


def register_tutor(client, first_name="Anthony", surname="Ozioko", email=None):
    email = email or helpers.unique_email("tutor")
    return client.post("/v1/auth/register", json={
        "email": email, "password": PASSWORD, "role": "tutor", "first_name": first_name, "surname": surname,
        "area": "Lekki", "offers": [helpers.offer()],
    })


def login(client, email, password=PASSWORD):
    return client.post("/v1/auth/login", json={"email": email, "password": password})


def test_tutor_gets_a_work_email_from_surname_initial_and_first_name(client):
    response = register_tutor(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["work_email"] == "o.anthony@tutorlink.com"
    assert body["tutor_profile"]["first_name"] == "Anthony"
    assert body["tutor_profile"]["surname"] == "Ozioko"
    assert body["tutor_profile"]["full_name"] == "Anthony Ozioko"


def test_same_name_gets_the_next_number(client):
    emails = [register_tutor(client).json()["user"]["work_email"] for _ in range(3)]
    assert emails == ["o.anthony@tutorlink.com", "o.anthony2@tutorlink.com", "o.anthony3@tutorlink.com"]


def test_name_is_reduced_to_plain_letters():
    assert local_part("Chí-Ọma Grace", "Ọkafor") == "o.chioma"
    assert local_part("  Anthony ", "van Dyk") == "v.anthony"


def test_tutor_logs_in_with_work_email_in_any_case(client):
    register_tutor(client)
    assert login(client, "o.anthony@tutorlink.com").status_code == 200
    assert login(client, "O.Anthony@tutorlink.com").status_code == 200


def test_tutor_personal_email_does_not_log_in_and_points_to_work_email(client):
    register_tutor(client, email="anthony@example.com")
    response = login(client, "anthony@example.com")
    assert response.status_code == 401
    assert "o.anthony@tutorlink.com" in response.json()["detail"]


def test_wrong_password_on_personal_email_reveals_nothing(client):
    register_tutor(client, email="anthony@example.com")
    response = login(client, "anthony@example.com", password="wrong-password")
    assert response.status_code == 401
    assert "tutorlink.com" not in response.json()["detail"]


def test_parents_have_no_work_email_and_log_in_with_their_own(client):
    parent = helpers.register_parent(client)
    me = client.get("/v1/auth/me", headers=parent["headers"]).json()
    assert me["user"]["work_email"] is None


def test_nobody_registers_with_a_tutorlink_address(client):
    for role in ("parent", "tutor"):
        body = {"email": "o.anthony@tutorlink.com", "password": PASSWORD, "role": role, "full_name": "Ada Parent"}
        if role == "tutor":
            body.update(first_name="Anthony", surname="Ozioko", area="Lekki", offers=[helpers.offer()])
        assert client.post("/v1/auth/register", json=body).status_code == 422


def test_tutor_needs_first_name_and_surname(client):
    assert register_tutor(client, surname="").status_code == 422
    assert register_tutor(client, first_name="   ").status_code == 422


def test_welcome_email_tells_the_tutor_their_work_email(client, outbox):
    register_tutor(client, email="anthony@example.com")
    email = outbox[-1]
    assert email["to"] == "anthony@example.com"
    assert "o.anthony@tutorlink.com" in email["html"]


def test_changing_name_keeps_the_work_email(client):
    tutor = helpers.register_tutor(client, full_name="Anthony Ozioko")
    response = client.post("/v1/tutors/profile", headers=tutor["headers"],
                           json={"first_name": "Tony", "surname": "Okafor", "area": "Lekki"})
    assert response.status_code == 200
    assert client.get("/v1/auth/me", headers=tutor["headers"]).json()["user"]["work_email"] == "o.anthony@tutorlink.com"
