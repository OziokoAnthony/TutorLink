"""Spec 2: job posts. Parents post what they need, approved tutors apply, the parent chooses one."""

from datetime import datetime, timedelta

import pytest

from tests import helpers

TUTOR_ONLY = {"tutor_fee_rate", "tutor_earning_per_lesson"}
PARENT_ONLY = {"parent_price_per_lesson", "booking_id", "applicant_count"}
PRIVATE = {"parent_surname", "parent_name", "address", "phone", "email", "parent_id", "parent_fee_rate"}


@pytest.fixture
def parent(client):
    return helpers.register_parent(client, full_name="Ada Okafor")


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers, full_name="Tunde Bakare")


@pytest.fixture
def job(client, parent):
    return helpers.post_job(client, parent)


def browse(client, tutor, **params):
    response = client.get("/v1/jobs", headers=tutor["headers"], params=params)
    assert response.status_code == 200, response.text
    return response.json()


def job_status(client, parent, job) -> str:
    return client.get(f"/v1/jobs/{job['id']}", headers=parent["headers"]).json()["status"]


# ---------- Posting ----------

def test_parent_posts_a_job_and_sees_their_price_but_no_tutor_fee(client, job):
    assert job["status"] == "open"
    assert job["price"] == "6000.00" and job["parent_price_per_lesson"] == "6600.00"
    assert not TUTOR_ONLY & job.keys()


@pytest.mark.parametrize("field", ["child_strengths", "child_weaknesses"])
def test_strengths_and_weaknesses_are_required(client, parent, field):
    for value in ("", "too short"):
        body = helpers.job_body(**{field: value})
        assert client.post("/v1/jobs", headers=parent["headers"], json=body).status_code == 422


def test_offline_job_needs_an_area(client, parent):
    body = helpers.job_body(area=None)
    assert client.post("/v1/jobs", headers=parent["headers"], json=body).status_code == 422
    online = helpers.job_body(mode="online", area=None)
    assert client.post("/v1/jobs", headers=parent["headers"], json=online).status_code == 201


def test_parent_needs_a_profile_picture_to_post(client):
    parent = helpers.register_parent(client, photo=False)
    assert client.post("/v1/jobs", headers=parent["headers"], json=helpers.job_body()).status_code == 409


def test_only_parents_post_jobs(client, tutor):
    assert client.post("/v1/jobs", headers=tutor["headers"], json=helpers.job_body()).status_code == 403


def test_three_subjects_one_price_found_by_any_of_them(client, parent, tutor):
    job = helpers.post_job(client, parent, subjects=["Mathematics", "Physics", "Chemistry"], price="7000.00")
    assert job["price"] == "7000.00"
    for subject in ("Mathematics", "physics", "CHEMISTRY"):
        assert [j["id"] for j in browse(client, tutor, subject=subject)] == [job["id"]]
    assert browse(client, tutor, subject="Biology") == []


# ---------- Browsing (tutor) ----------

def test_unapproved_tutor_cannot_browse_or_apply(client, job):
    pending = helpers.register_tutor(client)
    assert client.get("/v1/jobs", headers=pending["headers"]).status_code == 403
    assert helpers.apply_to_job(client, pending, job).status_code == 403


def test_tutor_sees_earning_first_name_and_picture_but_nothing_private(client, tutor, job):
    seen = browse(client, tutor)[0]
    assert seen["tutor_fee_rate"] == "0.0800" and seen["tutor_earning_per_lesson"] == "5520.00"
    assert seen["parent_first_name"] == "Ada" and "Okafor" not in str(seen)
    assert seen["parent_photo_url"]
    assert seen["child_strengths"] == helpers.STRENGTHS and seen["child_weaknesses"] == helpers.WEAKNESSES
    assert not (PARENT_ONLY | PRIVATE) & seen.keys()
    detail = client.get(f"/v1/jobs/{job['id']}", headers=tutor["headers"]).json()
    assert not (PARENT_ONLY | PRIVATE) & detail.keys()


def test_filters_by_level_mode_and_area(client, parent, tutor):
    lekki = helpers.post_job(client, parent, area="Lekki Phase 1")
    online = helpers.post_job(client, parent, mode="online", area=None)
    assert [j["id"] for j in browse(client, tutor, area="lekki")] == [lekki["id"]]
    assert [j["id"] for j in browse(client, tutor, mode="online")] == [online["id"]]
    assert browse(client, tutor, level="primary") == []


def test_parents_cannot_see_other_parents_jobs(client, job):
    other = helpers.register_parent(client)
    assert client.get(f"/v1/jobs/{job['id']}", headers=other["headers"]).status_code == 403
    assert client.get("/v1/jobs", headers=other["headers"]).status_code == 403


# ---------- Applying ----------

def test_apply_once_and_parent_is_notified(client, parent, tutor, job):
    response = helpers.apply_to_job(client, tutor, job)
    assert response.status_code == 201 and response.json()["my_application"]["status"] == "applied"
    assert helpers.apply_to_job(client, tutor, job).status_code == 409
    notes = client.get("/v1/notifications/me", headers=parent["headers"]).json()
    assert notes["items"][0]["title"] == "New applicant"


def test_applying_with_a_clashing_slot_is_409(client, paystack, tutor, job):
    other_parent = helpers.register_parent(client)
    helpers.accepted_booking(client, other_parent, tutor)  # same default time: 15:00-16:00 that weekday
    assert helpers.apply_to_job(client, tutor, job).status_code == 409


def test_tutor_withdraws_while_open(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    response = client.post(f"/v1/jobs/{job['id']}/withdraw", headers=tutor["headers"])
    assert response.status_code == 200 and response.json()["my_application"]["status"] == "withdrawn"
    assert client.get(f"/v1/jobs/{job['id']}/applications", headers=parent["headers"]).json() == []


def test_parent_sees_applicants_with_note_and_rating(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job, note="Ten years teaching WAEC maths.")
    applicants = client.get(f"/v1/jobs/{job['id']}/applications", headers=parent["headers"]).json()
    assert len(applicants) == 1
    assert applicants[0]["tutor_name"] == "Tunde Bakare" and applicants[0]["note"] == "Ten years teaching WAEC maths."
    assert applicants[0]["rating_count"] == 0
    assert client.get(f"/v1/tutors/{tutor['id']}").status_code == 200  # the full public profile


# ---------- Editing and closing ----------

def test_editing_an_open_job_notifies_applicants(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    response = client.put(f"/v1/jobs/{job['id']}", headers=parent["headers"],
                          json=helpers.job_body(price="6500.00"))
    assert response.status_code == 200 and response.json()["price"] == "6500.00"
    notes = client.get("/v1/notifications/me", headers=tutor["headers"]).json()
    assert notes["items"][0]["title"] == "A job you applied to changed"


def test_edit_that_clashes_withdraws_the_applicant_and_says_why(client, admin_headers, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    busy_day = helpers.days_ahead(4)
    helpers.accepted_booking(client, helpers.register_parent(client), tutor, start_date=busy_day)
    moved = [{"day_of_week": busy_day.weekday(), "start_time": "15:30", "end_time": "16:30"}]
    client.put(f"/v1/jobs/{job['id']}", headers=parent["headers"], json=helpers.job_body(slots=moved))
    mine = client.get(f"/v1/jobs/{job['id']}", headers=tutor["headers"]).json()["my_application"]
    assert mine["status"] == "withdrawn" and "clash" in mine["withdrawn_reason"]


def test_ongoing_or_closed_job_cannot_be_edited(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    assert helpers.choose_applicant(client, parent, job, tutor).status_code == 201
    assert client.put(f"/v1/jobs/{job['id']}", headers=parent["headers"], json=helpers.job_body()).status_code == 409
    other = helpers.post_job(client, parent)
    assert client.post(f"/v1/jobs/{other['id']}/close", headers=parent["headers"]).json()["status"] == "closed"
    assert client.put(f"/v1/jobs/{other['id']}", headers=parent["headers"], json=helpers.job_body()).status_code == 409


def test_open_job_with_no_applicants_never_expires(client, db, clock, parent, job):
    clock.travel(days=365)
    helpers.run_jobs(db, clock)
    assert job_status(client, parent, job) == "open"


# ---------- Choosing ----------

def test_choosing_books_the_tutor_and_takes_the_job_off_the_list(client, admin_headers, parent, tutor, job):
    rival = helpers.approved_tutor(client, admin_headers, full_name="Bola Ade")
    helpers.apply_to_job(client, tutor, job)
    helpers.apply_to_job(client, rival, job)

    response = helpers.choose_applicant(client, parent, job, tutor)
    assert response.status_code == 201, response.text
    booking = response.json()
    assert booking["status"] == "accepted" and booking["price"] == "6000.00" and booking["job_id"] == job["id"]
    assert booking["slots"] == job["slots"] and booking["child_strengths"] == helpers.STRENGTHS
    assert booking["periods"][0]["amount"] == "6600.00"

    assert job_status(client, parent, job) == "ongoing"
    assert browse(client, rival) == []
    rival_notes = client.get("/v1/notifications/me", headers=rival["headers"]).json()
    assert rival_notes["items"][0]["title"] == "Job taken"
    tutor_notes = client.get("/v1/notifications/me", headers=tutor["headers"]).json()
    assert tutor_notes["items"][0]["title"] == "You've been chosen"


def test_tutor_sees_the_booking_with_their_earning(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    booking = helpers.choose_applicant(client, parent, job, tutor).json()
    as_tutor = client.get(f"/v1/bookings/{booking['id']}", headers=tutor["headers"]).json()
    assert as_tutor["tutor_earning_per_lesson"] == "5520.00" and "parent_price_per_lesson" not in as_tutor


def test_paying_the_booking_from_a_job_confirms_its_lessons(client, paystack, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    booking = helpers.choose_applicant(client, parent, job, tutor).json()
    helpers.deposit(client, paystack, parent, booking["periods"][0]["amount"])
    lessons = helpers.lessons(client, parent)
    assert len(lessons) == 1 and lessons[0]["status"] == "confirmed" and lessons[0]["booking_id"] == booking["id"]


def test_unpaid_booking_releases_and_the_job_reopens(client, db, clock, admin_headers, parent, tutor, job):
    rival = helpers.approved_tutor(client, admin_headers, full_name="Bola Ade")
    helpers.apply_to_job(client, tutor, job)
    helpers.apply_to_job(client, rival, job)
    booking = helpers.choose_applicant(client, parent, job, tutor).json()
    clock.set(datetime.fromisoformat(booking["periods"][0]["due_at"]) + timedelta(minutes=1))
    helpers.run_jobs(db, clock)

    assert job_status(client, parent, job) == "open"
    applicants = client.get(f"/v1/jobs/{job['id']}/applications", headers=parent["headers"]).json()
    assert {a["status"] for a in applicants} == {"applied"}
    assert [j["id"] for j in browse(client, rival)] == [job["id"]]
    assert helpers.choose_applicant(client, parent, job, rival).status_code == 201


def test_job_completes_when_its_booking_ends(client, db, clock, paystack, admin_headers, parent, tutor):
    start = helpers.days_ahead(3)
    job = helpers.post_job(client, parent, start_date=start, end_date=start.isoformat())
    helpers.apply_to_job(client, tutor, job)
    booking = helpers.choose_applicant(client, parent, job, tutor).json()
    helpers.deposit(client, paystack, parent, booking["periods"][0]["amount"])
    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(minutes=5))
    helpers.run_jobs(db, clock)

    assert job_status(client, parent, job) == "completed"
    assert client.put(f"/v1/jobs/{job['id']}", headers=parent["headers"], json=helpers.job_body()).status_code == 409
    notes = client.get("/v1/notifications/me", headers=parent["headers"]).json()
    assert "Job completed" in [n["title"] for n in notes["items"]]
    newcomer = helpers.approved_tutor(client, admin_headers, full_name="Bola Ade")
    assert browse(client, newcomer) == []  # a completed job is no longer shown to tutors
    assert client.get(f"/v1/jobs/{job['id']}", headers=newcomer["headers"]).status_code == 404


def test_choosing_a_withdrawn_applicant_is_409(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    applicants = client.get(f"/v1/jobs/{job['id']}/applications", headers=parent["headers"]).json()
    client.post(f"/v1/jobs/{job['id']}/withdraw", headers=tutor["headers"])
    response = client.post(f"/v1/jobs/{job['id']}/applications/{applicants[0]['id']}/choose",
                           headers=parent["headers"])
    assert response.status_code == 409


def test_balance_matches_the_ledger_after_paying_a_job_booking(client, db, paystack, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    booking = helpers.choose_applicant(client, parent, job, tutor).json()
    helpers.deposit(client, paystack, parent, "10000.00")
    assert client.get("/v1/wallet/me", headers=parent["headers"]).json()["balance"] == "3400.00"
    assert booking["periods"][0]["amount"] == "6600.00"
    helpers.assert_ledger_matches(client, db, parent)


def test_only_the_owning_parent_manages_the_job(client, parent, tutor, job):
    helpers.apply_to_job(client, tutor, job)
    application = client.get(f"/v1/jobs/{job['id']}/applications", headers=parent["headers"]).json()[0]
    other = helpers.register_parent(client)
    base = f"/v1/jobs/{job['id']}"
    assert client.get(f"{base}/applications", headers=other["headers"]).status_code == 403
    assert client.put(base, headers=other["headers"], json=helpers.job_body()).status_code == 403
    assert client.post(f"{base}/close", headers=other["headers"]).status_code == 403
    assert client.post(f"{base}/applications/{application['id']}/choose", headers=other["headers"]).status_code == 403
    assert client.get(f"{base}/applications", headers=tutor["headers"]).status_code == 403
    assert job_status(client, parent, job) == "open"
