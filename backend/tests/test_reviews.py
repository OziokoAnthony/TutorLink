from decimal import Decimal

import pytest

from tests import helpers

MONDAYS = ["2025-10-06", "2025-10-13", "2025-10-20"]


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


def parent_with_confirmed_session(client, tutor, full_name="Ada Okafor", day=0, dates=MONDAYS[:1]):
    parent = helpers.register_parent(client, full_name=full_name)
    schedule = helpers.booked_schedule(client, parent, tutor, day=day)
    for d in dates:
        helpers.confirmed_session(client, parent, tutor, schedule["id"], d)
    return parent


def rate(client, parent, tutor, rating, comment=None):
    return client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=parent["headers"],
                      json={"rating": rating, "comment": comment})


def public_tutor(client, tutor) -> dict:
    return client.get(f"/v1/tutors/{tutor['id']}").json()


def test_parent_with_confirmed_session_can_rate(client, tutor):
    parent = parent_with_confirmed_session(client, tutor)
    response = rate(client, parent, tutor, 5, "Patient and clear")
    assert response.status_code == 200
    assert response.json()["rating"] == 5
    assert public_tutor(client, tutor)["average_rating"] == "5.00"
    assert public_tutor(client, tutor)["rating_count"] == 1


def test_cannot_rate_without_a_confirmed_session(client, tutor):
    stranger = helpers.register_parent(client)
    assert rate(client, stranger, tutor, 5).status_code == 403

    only_logged = helpers.register_parent(client)
    schedule = helpers.booked_schedule(client, only_logged, tutor)
    helpers.logged_session(client, tutor, schedule["id"], MONDAYS[0])
    assert rate(client, only_logged, tutor, 5).status_code == 403


def test_rating_again_updates_instead_of_duplicating(client, tutor):
    parent = parent_with_confirmed_session(client, tutor)
    rate(client, parent, tutor, 2, "Late twice")
    response = rate(client, parent, tutor, 4, "Much better now")
    assert response.json()["rating"] == 4
    assert public_tutor(client, tutor)["rating_count"] == 1
    assert public_tutor(client, tutor)["average_rating"] == "4.00"


def test_each_parent_counts_once_regardless_of_session_count(client, tutor):
    heavy_user = parent_with_confirmed_session(client, tutor, day=0, dates=MONDAYS)  # 3 sessions
    light_user = parent_with_confirmed_session(client, tutor, day=1, dates=["2025-10-07"])  # 1 session
    rate(client, heavy_user, tutor, 5)
    rate(client, light_user, tutor, 4)
    assert public_tutor(client, tutor)["average_rating"] == "4.50"
    assert public_tutor(client, tutor)["rating_count"] == 2


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_rating_must_be_1_to_5(client, tutor, rating):
    parent = parent_with_confirmed_session(client, tutor)
    assert rate(client, parent, tutor, rating).status_code == 422


def test_only_parents_can_rate(client, tutor, admin_headers):
    assert client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=tutor["headers"],
                      json={"rating": 5}).status_code == 403
    assert client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=admin_headers,
                      json={"rating": 5}).status_code == 403


def test_public_reviews_show_first_name_only(client, tutor):
    parent = parent_with_confirmed_session(client, tutor, full_name="Ada Okafor")
    rate(client, parent, tutor, 5, "  Excellent maths tutor  ")
    response = client.get(f"/v1/tutors/{tutor['id']}/reviews")
    assert response.status_code == 200
    review = response.json()[0]
    assert review["parent_first_name"] == "Ada"
    assert review["comment"] == "Excellent maths tutor"
    assert "Okafor" not in response.text
    assert parent["email"] not in response.text
    assert parent["id"] not in response.text


def test_reviews_of_unapproved_tutor_are_hidden(client):
    pending = helpers.register_tutor(client)
    assert client.get(f"/v1/tutors/{pending['id']}/reviews").status_code == 404


def test_unrated_tutor_has_no_average(client, tutor):
    assert public_tutor(client, tutor)["average_rating"] is None
    assert public_tutor(client, tutor)["rating_count"] == 0


def test_sort_by_rating_puts_best_first_and_unrated_last(client, admin_headers):
    good = helpers.approved_tutor(client, admin_headers, full_name="Zainab Good")
    best = helpers.approved_tutor(client, admin_headers, full_name="Yemi Best")
    unrated = helpers.approved_tutor(client, admin_headers, full_name="Aaron Unrated")
    rate(client, parent_with_confirmed_session(client, good), good, 4)
    rate(client, parent_with_confirmed_session(client, best), best, 5)

    by_rating = [t["user_id"] for t in client.get("/v1/tutors", params={"sort": "rating"}).json()]
    assert by_rating == [best["id"], good["id"], unrated["id"]]
    by_name = [t["user_id"] for t in client.get("/v1/tutors").json()]
    assert by_name == [unrated["id"], best["id"], good["id"]]


def test_more_ratings_win_a_tie(client, admin_headers):
    one_rating = helpers.approved_tutor(client, admin_headers, full_name="A One")
    two_ratings = helpers.approved_tutor(client, admin_headers, full_name="B Two")
    rate(client, parent_with_confirmed_session(client, one_rating), one_rating, 5)
    rate(client, parent_with_confirmed_session(client, two_ratings), two_ratings, 5)
    rate(client, parent_with_confirmed_session(client, two_ratings, day=1, dates=["2025-10-07"]), two_ratings, 5)
    by_rating = [t["user_id"] for t in client.get("/v1/tutors", params={"sort": "rating"}).json()]
    assert by_rating == [two_ratings["id"], one_rating["id"]]


def test_me_lists_tutors_to_rate_until_rated(client, tutor):
    parent = parent_with_confirmed_session(client, tutor)
    to_rate = client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"]
    assert [t["tutor_id"] for t in to_rate] == [tutor["id"]]
    assert to_rate[0]["full_name"] == "Tunde Tutor"

    rate(client, parent, tutor, 5)
    assert client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"] == []


def test_me_does_not_ask_to_rate_before_a_confirmed_session(client, tutor):
    parent = helpers.register_parent(client)
    schedule = helpers.booked_schedule(client, parent, tutor)
    helpers.logged_session(client, tutor, schedule["id"], MONDAYS[0])
    assert client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"] == []


def prompts(outbox, parent) -> list[str]:
    return [e["subject"] for e in outbox if e["to"] == parent["email"] and e["subject"].startswith("How was")]


def test_rating_prompt_email_after_first_confirmed_session_only(client, tutor, outbox):
    parent = parent_with_confirmed_session(client, tutor, dates=MONDAYS[:2])
    assert prompts(outbox, parent) == ["How was your lesson with Tunde Tutor?"]


def test_no_rating_prompt_if_already_rated(client, tutor, outbox):
    parent = helpers.register_parent(client)
    schedule = helpers.booked_schedule(client, parent, tutor)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], MONDAYS[0])
    rate(client, parent, tutor, 5)
    outbox.clear()
    helpers.confirmed_session(client, parent, tutor, schedule["id"], MONDAYS[1])
    assert prompts(outbox, parent) == []


def test_tutor_sees_own_rating_in_me(client, tutor):
    rate(client, parent_with_confirmed_session(client, tutor), tutor, 3)
    profile = client.get("/v1/auth/me", headers=tutor["headers"]).json()["tutor_profile"]
    assert Decimal(profile["average_rating"]) == Decimal("3")
    assert profile["rating_count"] == 1
