"""Spec 1 R4-R5: lesson reports, the parent's 24-hour problem window, and how problems are resolved."""

from datetime import datetime, timedelta

import pytest

from tests import helpers


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


@pytest.fixture
def lesson(client, paystack, parent, tutor):
    """A paid, confirmed lesson 3 days away."""
    helpers.paid_booking(client, paystack, parent, tutor)
    return helpers.lessons(client, parent)[0]


def ends(lesson) -> datetime:
    return datetime.fromisoformat(lesson["ends_at"])


def problem(client, parent, lesson, kind="tutor_absent"):
    return client.post(f"/v1/lessons/{lesson['id']}/problem", headers=parent["headers"],
                       json={"kind": kind, "description": "The tutor never showed up at all."})


def state(client, user, role="parent") -> dict:
    return helpers.lessons(client, user, role)[0]


# ---------- Reports ----------

def test_tutor_reports_after_the_lesson_and_parent_is_told(client, clock, parent, tutor, lesson):
    assert helpers.report(client, tutor, lesson["id"]).status_code == 409  # not over yet
    clock.set(ends(lesson) + timedelta(minutes=1))
    response = helpers.report(client, tutor, lesson["id"])
    assert response.status_code == 200 and response.json()["status"] == "reported"
    assert client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"][0]["title"] == \
        "Lesson report submitted"


def test_only_the_lessons_tutor_can_report(client, clock, admin_headers, lesson):
    clock.set(ends(lesson) + timedelta(minutes=1))
    other = helpers.approved_tutor(client, admin_headers)
    assert helpers.report(client, other, lesson["id"]).status_code == 403


def test_earning_becomes_payable_24_hours_after_the_report(client, db, clock, tutor, lesson):
    clock.set(ends(lesson) + timedelta(minutes=1))
    helpers.report(client, tutor, lesson["id"])
    clock.travel(hours=23)
    helpers.run_jobs(db, clock)
    assert state(client, tutor, "tutor")["earning_status"] == "pending"
    clock.travel(hours=1, minutes=1)
    helpers.run_jobs(db, clock)
    after = state(client, tutor, "tutor")
    assert after["status"] == "completed" and after["earning_status"] == "payable"


def test_no_report_within_24_hours_flags_the_lesson_and_holds_the_earning(client, db, clock, tutor, admin_headers,
                                                                        lesson):
    clock.set(ends(lesson) + timedelta(hours=24, minutes=1))
    helpers.run_jobs(db, clock)
    flagged = state(client, tutor, "tutor")
    assert flagged["status"] == "flagged" and flagged["earning_status"] == "on_hold"
    assert flagged["issue"]["kind"] == "no_report" and flagged["issue"]["raised_automatically"]
    assert helpers.report(client, tutor, lesson["id"]).status_code == 409
    assert client.get("/v1/admin/issues", headers=admin_headers).json()[0]["id"] == lesson["id"]


# ---------- Problems ----------

def test_parent_reports_a_problem_within_the_window_and_earning_is_held(client, clock, parent, tutor, lesson):
    clock.set(ends(lesson) + timedelta(minutes=1))
    helpers.report(client, tutor, lesson["id"])
    clock.travel(hours=23)
    response = problem(client, parent, lesson, "late_or_left_early")
    assert response.status_code == 200 and response.json()["status"] == "disputed"
    assert state(client, tutor, "tutor")["earning_status"] == "on_hold"


def test_problem_after_the_window_is_409(client, clock, parent, tutor, lesson):
    clock.set(ends(lesson) + timedelta(minutes=1))
    helpers.report(client, tutor, lesson["id"])
    clock.travel(hours=24, minutes=1)
    assert problem(client, parent, lesson).status_code == 409


def test_problem_before_the_lesson_is_409(client, parent, lesson):
    assert problem(client, parent, lesson).status_code == 409


def test_parent_can_report_absence_before_any_report(client, clock, parent, tutor, lesson):
    clock.set(ends(lesson) + timedelta(hours=2))
    assert problem(client, parent, lesson).status_code == 200
    # The tutor can still add a report, as their side of the story.
    assert helpers.report(client, tutor, lesson["id"]).status_code == 200
    assert state(client, parent)["status"] == "disputed"


def test_parent_adds_details_to_a_flagged_lesson(client, db, clock, parent, lesson):
    clock.set(ends(lesson) + timedelta(hours=25))
    helpers.run_jobs(db, clock)
    assert problem(client, parent, lesson).status_code == 200
    assert state(client, parent)["issue"]["kind"] == "tutor_absent"


def test_problem_kind_no_report_is_reserved(client, clock, parent, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    assert problem(client, parent, lesson, "no_report").status_code == 422


def test_only_the_lessons_parent_can_report_a_problem(client, clock, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    assert problem(client, helpers.register_parent(client), lesson).status_code == 403


# ---------- Resolution ----------

def resolve(client, admin_headers, lesson, **body):
    return client.post(f"/v1/admin/lessons/{lesson['id']}/resolve", headers=admin_headers, json=body)


def test_refund_returns_the_agreed_price_without_the_fee_and_voids_the_earning(client, db, clock, parent, tutor,
                                                                              admin_headers, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    problem(client, parent, lesson)
    response = resolve(client, admin_headers, lesson, resolution="refund", note="Tutor confirmed absence")
    assert response.status_code == 200 and response.json()["status"] == "refunded"
    wallet = client.get("/v1/wallet/me", headers=parent["headers"]).json()
    assert wallet["balance"] == "5000.00"  # paid 5,500; the 10% fee isn't refunded
    assert wallet["entries"][0]["kind"] == "refund"
    assert state(client, tutor, "tutor")["earning_status"] == "void"
    helpers.assert_ledger_matches(client, db, parent)


def test_reschedule_moves_the_lesson_and_clears_the_report(client, clock, parent, tutor, admin_headers, lesson):
    clock.set(ends(lesson) + timedelta(minutes=1))
    helpers.report(client, tutor, lesson["id"])
    problem(client, parent, lesson, "agreement_broken")
    new_date = (ends(lesson) + timedelta(days=2)).date()
    response = resolve(client, admin_headers, lesson, resolution="reschedule", new_date=new_date.isoformat(),
                       new_start_time="17:00", new_end_time="18:00")
    assert response.status_code == 200
    moved = response.json()
    assert moved["status"] == "confirmed" and moved["lesson_date"] == new_date.isoformat()
    assert moved["topic_covered"] is None and moved["earning_status"] == "pending"


def test_reschedule_to_the_past_is_422(client, clock, parent, admin_headers, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    problem(client, parent, lesson)
    response = resolve(client, admin_headers, lesson, resolution="reschedule",
                       new_date=ends(lesson).date().isoformat(), new_start_time="00:00", new_end_time="01:00")
    assert response.status_code == 422


def test_reject_completes_the_lesson_and_makes_it_payable(client, clock, parent, tutor, admin_headers, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    problem(client, parent, lesson)
    response = resolve(client, admin_headers, lesson, resolution="reject")
    assert response.json()["status"] == "completed"
    assert state(client, tutor, "tutor")["earning_status"] == "payable"
    assert resolve(client, admin_headers, lesson, resolution="reject").status_code == 409  # nothing open


def test_resolving_is_admin_only(client, clock, parent, lesson):
    clock.set(ends(lesson) + timedelta(hours=1))
    problem(client, parent, lesson)
    assert resolve(client, parent["headers"], lesson, resolution="reject").status_code == 403


def test_tutor_view_hides_parent_price_and_parent_view_hides_earning(client, parent, tutor, lesson):
    assert "tutor_earning" not in state(client, parent) and "earning_status" not in state(client, parent)
    assert "parent_price" not in state(client, tutor, "tutor")


def test_parents_no_longer_confirm_lessons(client, parent, lesson):
    """Spec 1 R4.1: paying confirms the lessons; the old parent confirm step is gone."""
    assert lesson["status"] == "confirmed"
    response = client.post(f"/v1/lessons/{lesson['id']}/confirm", headers=parent["headers"], json={})
    assert response.status_code in (404, 405)
