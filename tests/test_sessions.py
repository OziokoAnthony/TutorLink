from datetime import timedelta

import pytest
from sqlalchemy import text

from app.domains.sessions.service import today_in_nigeria
from tests import helpers


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def schedule(client, parent, tutor):
    return helpers.booked_schedule(client, parent, tutor)


def test_tutor_logs_session(client, tutor, schedule):
    response = helpers.log_session(client, tutor, schedule["id"], "2025-10-06")
    assert response.status_code == 201
    assert response.json()["status"] == "logged"
    assert response.json()["logged_by"] == tutor["id"]


def test_tutor_can_log_today(client, parent, tutor):
    today = today_in_nigeria()
    todays_schedule = helpers.booked_schedule(client, parent, tutor, day=today.weekday())
    assert helpers.log_session(client, tutor, todays_schedule["id"], today.isoformat()).status_code == 201


def test_future_session_date_is_rejected(client, parent, tutor):
    next_week = today_in_nigeria() + timedelta(days=7)
    future_schedule = helpers.booked_schedule(client, parent, tutor, day=next_week.weekday())
    assert helpers.log_session(client, tutor, future_schedule["id"], next_week.isoformat()).status_code == 422


def test_session_date_must_fall_on_the_schedule_weekday(client, tutor, schedule):
    response = helpers.log_session(client, tutor, schedule["id"], "2025-10-07")  # a Tuesday; schedule is Monday
    assert response.status_code == 422
    assert "Monday" in response.json()["detail"]


def test_cancelled_schedule_accepts_sessions_up_to_cancellation_only(client, db, parent, tutor, schedule):
    client.delete(f"/v1/schedules/{schedule['id']}", headers=parent["headers"])
    # Pretend the cancellation happened on Friday 10 October 2025.
    db.exec(text("UPDATE schedules SET updated_at = '2025-10-10 12:00:00+01' WHERE id = :id"),
            params={"id": schedule["id"]})
    db.commit()

    assert helpers.log_session(client, tutor, schedule["id"], "2025-10-06").status_code == 201
    response = helpers.log_session(client, tutor, schedule["id"], "2025-10-13")
    assert response.status_code == 409
    assert response.json()["detail"] == "Schedule was cancelled before this date"


def test_logging_same_schedule_and_date_twice_is_409(client, tutor, schedule):
    helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    assert helpers.log_session(client, tutor, schedule["id"], "2025-10-06").status_code == 409


def test_tutor_cannot_log_for_schedule_they_dont_own(client, admin_headers, schedule):
    other_tutor = helpers.approved_tutor(client, admin_headers)
    assert helpers.log_session(client, other_tutor, schedule["id"], "2025-10-06").status_code == 403


def test_parent_confirms_own_logged_session(client, parent, tutor, schedule):
    session = helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    response = client.patch(f"/v1/sessions/{session['id']}/confirm", headers=parent["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["confirmed_by"] == parent["id"]


def test_parent_cannot_confirm_another_parents_session(client, tutor, schedule):
    session = helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    other_parent = helpers.register_parent(client)
    response = client.patch(f"/v1/sessions/{session['id']}/confirm", headers=other_parent["headers"])
    assert response.status_code == 403


def test_cannot_confirm_twice_or_cancel_confirmed(client, parent, tutor, schedule):
    session = helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    assert client.patch(f"/v1/sessions/{session['id']}/confirm", headers=parent["headers"]).status_code == 409
    assert client.patch(f"/v1/sessions/{session['id']}/cancel", headers=parent["headers"]).status_code == 409


def test_parent_cancels_logged_session(client, parent, tutor, schedule):
    session = helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    response = client.patch(f"/v1/sessions/{session['id']}/cancel", headers=parent["headers"])
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert client.patch(f"/v1/sessions/{session['id']}/confirm", headers=parent["headers"]).status_code == 409


def test_parent_cannot_cancel_another_parents_session(client, tutor, schedule):
    session = helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    other_parent = helpers.register_parent(client)
    assert client.patch(f"/v1/sessions/{session['id']}/cancel", headers=other_parent["headers"]).status_code == 403


def test_session_lists_with_filters(client, parent, tutor, schedule):
    helpers.logged_session(client, tutor, schedule["id"], "2025-09-29")
    october = helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    client.patch(f"/v1/sessions/{october['id']}/confirm", headers=parent["headers"])

    mine = client.get("/v1/sessions/me", headers=parent["headers"]).json()
    assert len(mine) == 2
    october_only = client.get("/v1/sessions/me", headers=parent["headers"], params={"month": 10, "year": 2025}).json()
    assert [s["id"] for s in october_only] == [october["id"]]
    confirmed = client.get("/v1/sessions/tutor/me", headers=tutor["headers"], params={"status": "confirmed"}).json()
    assert [s["id"] for s in confirmed] == [october["id"]]
    assert client.get("/v1/sessions/me", headers=helpers.register_parent(client)["headers"]).json() == []


def test_admin_sessions_is_admin_only(client, admin_headers, parent, tutor, schedule):
    helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    assert len(client.get("/v1/admin/sessions", headers=admin_headers).json()) == 1
    assert client.get("/v1/admin/sessions", headers=parent["headers"]).status_code == 403
