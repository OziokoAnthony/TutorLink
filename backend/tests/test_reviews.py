from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from tests import helpers


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


@pytest.fixture
def teach(client, db, clock, paystack):
    """teach([(parent, tutor), ...], lessons_each=1): books every pair on the same day at different
    times, then the lessons happen, are reported, and complete. Returns the parents."""
    def run(pairs, lessons_each=1):
        day = helpers.days_ahead(3, clock.now())
        hour = 8
        for parent, tutor in pairs:
            slots = []
            for _ in range(lessons_each):
                slots.append({"day_of_week": day.weekday(), "start_time": f"{hour:02d}:00",
                              "end_time": f"{hour:02d}:45"})
                hour += 1
            helpers.paid_booking(client, paystack, parent, tutor, start_date=day, slots=slots)
        tutors = {t["id"]: t for _, t in pairs}
        taught = [(t, l) for t in tutors.values() for l in helpers.lessons(client, t, "tutor")
                  if l["status"] == "confirmed"]
        clock.set(max(datetime.fromisoformat(l["ends_at"]) for _, l in taught) + timedelta(minutes=5))
        for t, l in taught:
            assert helpers.report(client, t, l["id"]).status_code == 200
        clock.travel(hours=24, minutes=1)
        helpers.run_jobs(db, clock)
        return [p for p, _ in pairs]
    return run


def parent_with_completed_lesson(client, teach, tutor, full_name="Ada Okafor", lessons_each=1):
    parent = helpers.register_parent(client, full_name=full_name)
    teach([(parent, tutor)], lessons_each)
    return parent


def rate(client, parent, tutor, rating, comment=None):
    return client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=parent["headers"],
                      json={"rating": rating, "comment": comment})


def public_tutor(client, tutor) -> dict:
    return client.get(f"/v1/tutors/{tutor['id']}").json()


def test_parent_with_completed_lesson_can_rate(client, teach, tutor):
    parent = parent_with_completed_lesson(client, teach, tutor)
    response = rate(client, parent, tutor, 5, "Patient and clear")
    assert response.status_code == 200
    assert response.json()["rating"] == 5
    assert public_tutor(client, tutor)["average_rating"] == "5.00"
    assert public_tutor(client, tutor)["rating_count"] == 1


def test_cannot_rate_without_a_completed_lesson(client, paystack, tutor):
    stranger = helpers.register_parent(client)
    assert rate(client, stranger, tutor, 5).status_code == 403

    only_booked = helpers.register_parent(client)
    helpers.paid_booking(client, paystack, only_booked, tutor)  # lesson not taught yet
    assert rate(client, only_booked, tutor, 5).status_code == 403


def test_rating_again_updates_instead_of_duplicating(client, teach, tutor):
    parent = parent_with_completed_lesson(client, teach, tutor)
    rate(client, parent, tutor, 2, "Late twice")
    response = rate(client, parent, tutor, 4, "Much better now")
    assert response.json()["rating"] == 4
    assert public_tutor(client, tutor)["rating_count"] == 1
    assert public_tutor(client, tutor)["average_rating"] == "4.00"


def test_each_parent_counts_once_regardless_of_lesson_count(client, teach, tutor):
    heavy_user, light_user = helpers.register_parent(client), helpers.register_parent(client)
    teach([(heavy_user, tutor)], lessons_each=3)
    teach([(light_user, tutor)])
    rate(client, heavy_user, tutor, 5)
    rate(client, light_user, tutor, 2)
    assert public_tutor(client, tutor)["average_rating"] == "3.50"
    assert public_tutor(client, tutor)["rating_count"] == 2


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_must_be_1_to_5(client, teach, tutor, rating):
    parent = parent_with_completed_lesson(client, teach, tutor)
    assert rate(client, parent, tutor, rating).status_code == 422


def test_only_parents_can_rate(client, tutor, admin_headers):
    assert client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=tutor["headers"],
                      json={"rating": 5}).status_code == 403
    assert client.put(f"/v1/tutors/{tutor['id']}/reviews", headers=admin_headers,
                      json={"rating": 5}).status_code == 403


def test_public_reviews_show_first_name_only(client, teach, tutor):
    parent = parent_with_completed_lesson(client, teach, tutor, full_name="Ada Okafor")
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


def test_sort_by_rating_puts_best_first_and_unrated_last(client, teach, admin_headers):
    good = helpers.approved_tutor(client, admin_headers, full_name="Zainab Good")
    best = helpers.approved_tutor(client, admin_headers, full_name="Yemi Best")
    unrated = helpers.approved_tutor(client, admin_headers, full_name="Aaron Unrated")
    p1, p2 = teach([(helpers.register_parent(client), good), (helpers.register_parent(client), best)])
    rate(client, p1, good, 4)
    rate(client, p2, best, 5)

    by_rating = [t["user_id"] for t in client.get("/v1/tutors", params={"sort": "rating"}).json()]
    assert by_rating == [best["id"], good["id"], unrated["id"]]
    by_name = [t["user_id"] for t in client.get("/v1/tutors").json()]
    assert by_name == [unrated["id"], best["id"], good["id"]]


def test_more_ratings_win_a_tie(client, teach, admin_headers):
    one_rating = helpers.approved_tutor(client, admin_headers, full_name="A One")
    two_ratings = helpers.approved_tutor(client, admin_headers, full_name="B Two")
    p1, p2, p3 = teach([(helpers.register_parent(client), one_rating), (helpers.register_parent(client), two_ratings),
                        (helpers.register_parent(client), two_ratings)])
    rate(client, p1, one_rating, 5)
    rate(client, p2, two_ratings, 5)
    rate(client, p3, two_ratings, 5)
    by_rating = [t["user_id"] for t in client.get("/v1/tutors", params={"sort": "rating"}).json()]
    assert by_rating == [two_ratings["id"], one_rating["id"]]


def test_me_lists_tutors_to_rate_until_rated(client, teach, tutor):
    parent = parent_with_completed_lesson(client, teach, tutor)
    to_rate = client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"]
    assert [t["tutor_id"] for t in to_rate] == [tutor["id"]]
    assert to_rate[0]["full_name"] == "Tunde Tutor"

    rate(client, parent, tutor, 5)
    assert client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"] == []


def test_me_does_not_ask_to_rate_before_a_completed_lesson(client, paystack, tutor):
    parent = helpers.register_parent(client)
    helpers.paid_booking(client, paystack, parent, tutor)
    assert client.get("/v1/auth/me", headers=parent["headers"]).json()["tutors_to_rate"] == []


def prompts(outbox, parent) -> list[str]:
    return [e["subject"] for e in outbox if e["to"] == parent["email"] and e["subject"].startswith("How was")]


def test_rating_prompt_once_even_when_two_lessons_complete_together(client, teach, tutor, outbox):
    parent = parent_with_completed_lesson(client, teach, tutor, lessons_each=2)
    assert prompts(outbox, parent) == ["How was your lesson with Tunde Tutor?"]


def test_no_rating_prompt_if_already_rated(client, teach, tutor, outbox):
    parent = parent_with_completed_lesson(client, teach, tutor)
    rate(client, parent, tutor, 5)
    outbox.clear()
    teach([(parent, tutor)])
    assert prompts(outbox, parent) == []


def test_tutor_sees_own_rating_in_me(client, teach, tutor):
    rate(client, parent_with_completed_lesson(client, teach, tutor), tutor, 3)
    profile = client.get("/v1/auth/me", headers=tutor["headers"]).json()["tutor_profile"]
    assert Decimal(profile["average_rating"]) == Decimal("3")
    assert profile["rating_count"] == 1
