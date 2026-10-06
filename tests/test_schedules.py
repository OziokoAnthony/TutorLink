import pytest

from tests import helpers


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


def test_parent_books_valid_slot(client, parent, tutor):
    response = helpers.book(client, parent, tutor)
    assert response.status_code == 201
    assert response.json()["is_active"] is True
    assert response.json()["parent_id"] == parent["id"]


@pytest.mark.parametrize("start,end", [
    ("14:30", "15:30"),  # overlaps the start
    ("15:00", "16:00"),  # exact match
    ("15:30", "16:30"),  # overlaps the end
    ("14:00", "16:30"),  # contains the existing slot
])
def test_clashing_slot_same_tutor_is_409(client, parent, tutor, start, end):
    helpers.booked_schedule(client, parent, tutor, start="15:00", end="16:00")
    other_parent = helpers.register_parent(client)
    response = helpers.book(client, other_parent, tutor, start=start, end=end)
    assert response.status_code == 409
    assert response.json()["detail"] == "Tutor already has a session at this time."


@pytest.mark.parametrize("start,end", [("14:00", "15:00"), ("16:00", "17:00")])
def test_back_to_back_slots_are_allowed(client, parent, tutor, start, end):
    helpers.booked_schedule(client, parent, tutor, start="15:00", end="16:00")
    assert helpers.book(client, parent, tutor, start=start, end=end).status_code == 201


def test_same_time_on_another_day_is_allowed(client, parent, tutor):
    helpers.booked_schedule(client, parent, tutor, day=0)
    assert helpers.book(client, parent, tutor, day=1).status_code == 201


def test_cancelled_slot_no_longer_clashes(client, parent, tutor):
    schedule = helpers.booked_schedule(client, parent, tutor)
    client.delete(f"/v1/schedules/{schedule['id']}", headers=parent["headers"])
    assert helpers.book(client, parent, tutor).status_code == 201


def test_parent_cancels_own_schedule(client, parent, tutor):
    schedule = helpers.booked_schedule(client, parent, tutor)
    response = client.delete(f"/v1/schedules/{schedule['id']}", headers=parent["headers"])
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/v1/schedules/me", headers=parent["headers"]).json() == []


def test_parent_cannot_cancel_another_parents_schedule(client, parent, tutor):
    schedule = helpers.booked_schedule(client, parent, tutor)
    other_parent = helpers.register_parent(client)
    response = client.delete(f"/v1/schedules/{schedule['id']}", headers=other_parent["headers"])
    assert response.status_code == 403


def test_tutor_cannot_create_schedule(client, tutor):
    response = client.post("/v1/schedules", headers=tutor["headers"], json={
        "tutor_id": tutor["id"], "day_of_week": 0, "start_time": "15:00", "end_time": "16:00",
        "subject": "Mathematics", "level": "senior_secondary",
    })
    assert response.status_code == 403


def test_cannot_book_unapproved_tutor(client, parent):
    pending = helpers.register_tutor(client)
    helpers.add_subject(client, pending)
    assert helpers.book(client, parent, pending).status_code == 404


def test_cannot_book_subject_tutor_does_not_teach(client, parent, tutor):
    assert helpers.book(client, parent, tutor, subject="Physics").status_code == 422


def test_end_time_must_be_after_start_time(client, parent, tutor):
    assert helpers.book(client, parent, tutor, start="16:00", end="15:00").status_code == 422


def test_my_schedules_lists_only_my_active_schedules(client, parent, tutor):
    mine = helpers.booked_schedule(client, parent, tutor, day=0)
    helpers.booked_schedule(client, helpers.register_parent(client), tutor, day=1)
    response = client.get("/v1/schedules/me", headers=parent["headers"])
    assert [s["id"] for s in response.json()] == [mine["id"]]


def test_tutor_schedule_shows_booked_slots_without_parent(client, parent, tutor):
    helpers.booked_schedule(client, parent, tutor)
    response = client.get(f"/v1/tutors/{tutor['id']}/schedule", headers=parent["headers"])
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "parent_id" not in response.json()[0]
    assert client.get(f"/v1/tutors/{tutor['id']}/schedule").status_code == 401
