from tests import helpers
from tests.helpers import PASSWORD


def register(client, **overrides):
    body = {"email": helpers.unique_email("user"), "password": PASSWORD, "role": "parent",
            "full_name": "Ada Parent"}
    if overrides.get("role") == "tutor":
        body = {**body, "full_name": None, "first_name": "Anthony", "surname": "Ozioko"}
        del body["password"]
    body.update(overrides)
    return client.post("/v1/auth/register", json=body)


def test_register_parent_returns_201_with_parent_profile(client):
    response = register(client, phone="08012345678", address="123 Ikegbunam Street, Abakpa")
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "parent"
    assert body["parent_profile"]["full_name"] == "Ada Parent"
    assert body["tutor_profile"] is None


def test_register_tutor_returns_201_with_pending_vetting_and_offers(client):
    response = register(client, role="tutor", area="Yaba",
                        offers=[helpers.offer(subjects=["Mathematics", "Physics"], price="4500.00")])
    assert response.status_code == 201
    profile = response.json()["tutor_profile"]
    assert profile["vetting_status"] == "pending"
    assert profile["area"] == "Yaba"
    assert profile["offers"][0]["subjects"] == ["Mathematics", "Physics"]
    assert profile["offers"][0]["price"] == "4500.00"  # one price, whatever the number of subjects


def test_register_tutor_without_area_or_offer_is_422(client):
    assert register(client, role="tutor", offers=[helpers.offer()]).status_code == 422
    assert register(client, role="tutor", area="Yaba").status_code == 422
    assert register(client, role="tutor", area="Yaba", offers=[]).status_code == 422


def test_register_as_admin_is_rejected(client):
    assert register(client, role="admin").status_code == 422


def test_register_duplicate_email_is_409(client):
    assert register(client, email="dup@example.com").status_code == 201
    assert register(client, email="dup@example.com").status_code == 409


def test_duplicate_check_is_case_insensitive_and_email_stored_lowercase(client):
    first = register(client, email="Mixed.Case@Example.com")
    assert first.status_code == 201
    assert first.json()["user"]["email"] == "mixed.case@example.com"
    assert register(client, email="MIXED.case@example.COM").status_code == 409


def test_login_with_correct_credentials_returns_token(client):
    parent = helpers.register_parent(client)
    response = client.post("/v1/auth/login", json={"email": parent["email"].upper(), "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_login_with_wrong_password_is_401(client):
    parent = helpers.register_parent(client)
    response = client.post("/v1/auth/login", json={"email": parent["email"], "password": "wrong-password"})
    assert response.status_code == 401


def test_login_with_unknown_email_is_401(client):
    response = client.post("/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert response.status_code == 401


def test_me_with_valid_token_returns_user_and_profile(client):
    parent = helpers.register_parent(client)
    response = client.get("/v1/auth/me", headers=parent["headers"])
    assert response.status_code == 200
    assert response.json()["user"]["email"] == parent["email"]
    assert response.json()["parent_profile"]["full_name"] == "Ada Parent"


def test_me_without_token_is_401(client):
    assert client.get("/v1/auth/me").status_code == 401


def test_me_with_invalid_token_is_401(client):
    assert client.get("/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_password_hash_never_in_any_response(client):
    responses = [
        register(client, email="parent@example.com"),
        register(client, email="tutor@example.com", role="tutor", area="Ikeja", offers=[helpers.offer()]),
    ]
    headers = helpers.login(client, "parent@example.com")
    responses.append(client.post("/v1/auth/login", json={"email": "parent@example.com", "password": PASSWORD}))
    responses.append(client.get("/v1/auth/me", headers=headers))
    tutor_login = responses[1].json()["user"]["work_email"]
    responses.append(client.get("/v1/auth/me", headers=helpers.login(client, tutor_login)))
    for response in responses:
        assert "password_hash" not in response.text
        assert "$2b$" not in response.text  # no bcrypt hash under any other name
