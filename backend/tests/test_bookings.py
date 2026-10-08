"""Spec 1 R0-R2: booking requests, the tutor's answer, cancelling and ending, and who sees what."""

from datetime import datetime, timedelta

import pytest

from tests import helpers

PARENT_ONLY = {"parent_price_per_lesson", "periods"}
TUTOR_ONLY = {"tutor_fee_rate", "tutor_earning_per_lesson"}
ADMIN_ONLY = {"parent_fee_rate", "platform_margin_per_lesson"}


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


# ---------- Requesting ----------

def test_parent_requests_a_booking_and_tutor_is_notified(client, parent, tutor):
    booking = helpers.requested_booking(client, parent, tutor)
    assert booking["status"] == "requested"
    assert booking["price"] == "5000.00"
    assert booking["child_strengths"] == helpers.STRENGTHS
    as_tutor = client.get(f"/v1/bookings/{booking['id']}", headers=tutor["headers"]).json()
    assert as_tutor["child_strengths"] == helpers.STRENGTHS and as_tutor["child_weaknesses"] == helpers.WEAKNESSES
    notes = client.get("/v1/notifications/me", headers=tutor["headers"]).json()
    assert notes["unread_count"] == 1 and notes["items"][0]["title"] == "New booking request"


@pytest.mark.parametrize("field", ["strengths", "weaknesses"])
def test_child_strengths_and_weaknesses_are_required(client, parent, tutor, field):
    assert helpers.book(client, parent, tutor, **{field: ""}).status_code == 422
    assert helpers.book(client, parent, tutor, **{field: "too short"}).status_code == 422


def test_parent_needs_a_profile_picture_to_book(client, tutor):
    parent = helpers.register_parent(client, photo=False)
    response = helpers.book(client, parent, tutor)
    assert response.status_code == 409
    assert "profile picture" in response.json()["detail"]


def test_slot_must_be_inside_the_offers_available_times(client, parent, admin_headers):
    tutor = helpers.approved_tutor(client, admin_headers, windows=[
        {"day_of_week": d, "start_time": "16:00", "end_time": "18:00"} for d in range(7)])
    start = helpers.days_ahead(3)
    inside = [{"day_of_week": start.weekday(), "start_time": "16:00", "end_time": "17:00"}]
    outside = [{"day_of_week": start.weekday(), "start_time": "15:30", "end_time": "16:30"}]
    assert helpers.book(client, parent, tutor, slots=outside).status_code == 422
    assert helpers.book(client, parent, tutor, slots=inside).status_code == 201


def test_subjects_must_come_from_the_offer(client, parent, admin_headers):
    tutor = helpers.approved_tutor(client, admin_headers, subjects=["Mathematics", "Physics"])
    assert helpers.book(client, parent, tutor, subjects=["Chemistry"]).status_code == 422
    booking = helpers.requested_booking(client, parent, tutor, subjects=["physics", "mathematics"])
    assert booking["subjects"] == ["Physics", "Mathematics"]  # tutor's spelling


def test_unapproved_tutor_cannot_be_booked(client, parent):
    tutor = helpers.register_tutor(client)
    assert helpers.book(client, parent, tutor).status_code == 404


def test_start_date_in_the_past_is_rejected(client, parent, tutor):
    assert helpers.book(client, parent, tutor, start_date=helpers.days_ahead(-1)).status_code == 422


def test_only_parents_can_request(client, tutor, admin_headers):
    other_tutor = helpers.approved_tutor(client, admin_headers)
    assert helpers.book(client, other_tutor, tutor).status_code == 403


# ---------- Clashes ----------

def test_clash_with_an_accepted_booking_is_409(client, parent, tutor):
    helpers.accepted_booking(client, parent, tutor)
    other = helpers.register_parent(client)
    response = helpers.book(client, other, tutor)
    assert response.status_code == 409
    assert response.json()["detail"] == "Tutor already has a session at this time."


def test_back_to_back_slots_are_allowed(client, parent, tutor):
    helpers.accepted_booking(client, parent, tutor)
    start = helpers.days_ahead(3)
    after = [{"day_of_week": start.weekday(), "start_time": "16:00", "end_time": "17:00"}]
    assert helpers.book(client, helpers.register_parent(client), tutor, slots=after).status_code == 201


def test_two_requests_for_the_same_time_only_one_can_be_accepted(client, tutor):
    first = helpers.requested_booking(client, helpers.register_parent(client), tutor)
    second = helpers.requested_booking(client, helpers.register_parent(client), tutor)
    assert client.post(f"/v1/bookings/{first['id']}/accept", headers=tutor["headers"]).status_code == 200
    assert client.post(f"/v1/bookings/{second['id']}/accept", headers=tutor["headers"]).status_code == 409


# ---------- The tutor's answer ----------

def test_accept_creates_first_period_and_tells_parent_amount_and_account_number(client, parent, tutor, paystack):
    booking = helpers.accepted_booking(client, parent, tutor)
    assert booking["status"] == "accepted"
    period = booking["periods"][0]
    assert period["status"] == "due" and period["lesson_count"] == 1
    assert period["amount"] == "5500.00"  # ₦5,000 + 10% parent fee
    wallet = client.get("/v1/wallet/me", headers=parent["headers"]).json()
    assert wallet["virtual_account"]["account_number"].startswith("90")
    assert wallet["amount_due"] == "5500.00"
    taken = client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"][0]
    assert taken["title"] == "Your booking has been taken"
    assert "5,500.00" in taken["body"] and wallet["virtual_account"]["account_number"] in taken["body"]


def test_first_lesson_less_than_24_hours_away_moves_to_the_next_slot(client, parent, tutor, clock):
    tomorrow = helpers.days_ahead(1)
    slot = [{"day_of_week": tomorrow.weekday(), "start_time": "08:00", "end_time": "09:00"}]
    booking = helpers.requested_booking(client, parent, tutor, start_date=tomorrow, slots=slot)
    client.post(f"/v1/bookings/{booking['id']}/accept", headers=tutor["headers"])
    period = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["periods"][0]
    assert period["starts_on"] in (tomorrow.isoformat(), (tomorrow + timedelta(days=7)).isoformat())


def test_decline_notifies_parent(client, parent, tutor):
    booking = helpers.requested_booking(client, parent, tutor)
    response = client.post(f"/v1/bookings/{booking['id']}/decline", headers=tutor["headers"], json={})
    assert response.status_code == 200 and response.json()["status"] == "declined"
    assert client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"][0]["title"] == "Booking declined"


def test_only_the_booked_tutor_can_answer(client, parent, tutor, admin_headers):
    booking = helpers.requested_booking(client, parent, tutor)
    other = helpers.approved_tutor(client, admin_headers)
    assert client.post(f"/v1/bookings/{booking['id']}/accept", headers=other["headers"]).status_code == 403


def test_unanswered_request_expires_after_72_hours(client, db, clock, parent, tutor):
    booking = helpers.requested_booking(client, parent, tutor)
    clock.travel(hours=71)
    helpers.run_jobs(db, clock)
    assert client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["status"] == "requested"
    clock.travel(hours=2)
    helpers.run_jobs(db, clock)
    assert client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["status"] == "expired"
    assert client.post(f"/v1/bookings/{booking['id']}/accept", headers=tutor["headers"]).status_code == 409


# ---------- Fees and visibility ----------

def test_each_side_sees_only_its_own_fee(client, parent, tutor, admin_headers):
    booking = helpers.accepted_booking(client, parent, tutor)
    as_parent = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()
    as_tutor = client.get(f"/v1/bookings/{booking['id']}", headers=tutor["headers"]).json()
    as_admin = client.get(f"/v1/bookings/{booking['id']}", headers=admin_headers).json()

    assert as_parent["parent_price_per_lesson"] == "5500.00"
    assert not (TUTOR_ONLY | ADMIN_ONLY) & as_parent.keys()
    assert as_tutor["tutor_earning_per_lesson"] == "4600.00" and as_tutor["tutor_fee_rate"] == "0.0800"
    assert not (PARENT_ONLY | ADMIN_ONLY) & as_tutor.keys()
    assert as_admin["platform_margin_per_lesson"] == "900.00"
    assert as_parent["price"] == as_tutor["price"] == "5000.00"


def test_lists_use_the_same_views(client, parent, tutor):
    helpers.accepted_booking(client, parent, tutor)
    assert not (TUTOR_ONLY | ADMIN_ONLY) & client.get("/v1/bookings/me", headers=parent["headers"]).json()[0].keys()
    assert not (PARENT_ONLY | ADMIN_ONLY) & client.get("/v1/bookings/tutor/me", headers=tutor["headers"]).json()[0].keys()


def test_tutor_sees_parent_photo_and_parent_sees_tutor_photo(client, parent, tutor):
    helpers.upload_photo(client, tutor["headers"])
    booking = helpers.requested_booking(client, parent, tutor)
    assert client.get(f"/v1/bookings/{booking['id']}", headers=tutor["headers"]).json()["parent_photo_url"]
    assert client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["tutor_photo_url"]


def test_strangers_cannot_see_a_booking(client, parent, tutor):
    booking = helpers.requested_booking(client, parent, tutor)
    stranger = helpers.register_parent(client)
    assert client.get(f"/v1/bookings/{booking['id']}", headers=stranger["headers"]).status_code == 403


def test_changing_fees_does_not_change_an_accepted_booking(client, parent, tutor, admin_headers):
    booking = helpers.accepted_booking(client, parent, tutor)
    assert client.put("/v1/admin/fees", headers=admin_headers,
                      json={"parent_fee_rate": "0.20", "tutor_fee_rate": "0.15"}).status_code == 200
    after = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()
    assert after["parent_price_per_lesson"] == "5500.00" and after["periods"][0]["amount"] == "5500.00"
    newer = helpers.accepted_booking(client, helpers.register_parent(client), tutor,
                                     start_date=helpers.days_ahead(4))
    assert newer["parent_price_per_lesson"] == "6000.00"


def test_editing_an_offer_does_not_change_a_booking(client, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    client.put(f"/v1/tutors/profile/offers/{tutor['offer_id']}", headers=tutor["headers"],
               json=helpers.offer(price="8000.00"))
    assert client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["price"] == "5000.00"


def test_fees_are_admin_only(client, parent):
    assert client.get("/v1/admin/fees", headers=parent["headers"]).status_code == 403


# ---------- Cancelling and ending ----------

def test_cancel_with_48_hours_notice_requests_refund_of_agreed_price(client, db, paystack, parent, tutor,
                                                                    admin_headers):
    booking = helpers.paid_booking(client, paystack, parent, tutor)  # first lesson in 3 days
    response = client.post(f"/v1/bookings/{booking['id']}/cancel", headers=parent["headers"], json={})
    assert response.status_code == 200 and response.json()["status"] == "cancelled"
    refund = client.get("/v1/admin/refunds", headers=admin_headers).json()[0]
    assert refund["status"] == "pending" and refund["amount"] == "5000.00"  # fee excluded
    assert helpers.lessons(client, parent)[0]["status"] == "cancelled"

    approved = client.post(f"/v1/admin/refunds/{refund['id']}/approve", headers=admin_headers, json={})
    assert approved.json()["status"] == "approved"
    assert client.get("/v1/wallet/me", headers=parent["headers"]).json()["balance"] == "5000.00"
    helpers.assert_ledger_matches(client, db, parent)


def test_cancel_with_less_than_48_hours_notice_refunds_nothing(client, paystack, clock, parent, tutor, admin_headers):
    booking = helpers.paid_booking(client, paystack, parent, tutor)
    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["starts_at"]) - timedelta(hours=47))
    client.post(f"/v1/bookings/{booking['id']}/cancel", headers=parent["headers"], json={})
    assert client.get("/v1/admin/refunds", headers=admin_headers).json() == []
    assert helpers.lessons(client, parent)[0]["status"] == "confirmed"  # still goes ahead


def test_rejected_refund_adds_nothing(client, paystack, parent, tutor, admin_headers):
    booking = helpers.paid_booking(client, paystack, parent, tutor)
    client.post(f"/v1/bookings/{booking['id']}/cancel", headers=parent["headers"], json={})
    refund = client.get("/v1/admin/refunds", headers=admin_headers).json()[0]
    client.post(f"/v1/admin/refunds/{refund['id']}/reject", headers=admin_headers, json={"note": "No"})
    assert client.get("/v1/wallet/me", headers=parent["headers"]).json()["balance"] == "0.00"
    assert client.post(f"/v1/admin/refunds/{refund['id']}/approve", headers=admin_headers, json={}).status_code == 409


def test_cancelling_frees_the_slot(client, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    client.post(f"/v1/bookings/{booking['id']}/cancel", headers=parent["headers"], json={})
    assert helpers.book(client, helpers.register_parent(client), tutor).status_code == 201


def test_either_side_can_end_and_paid_lessons_still_happen(client, paystack, parent, tutor):
    booking = helpers.paid_booking(client, paystack, parent, tutor)
    response = client.post(f"/v1/bookings/{booking['id']}/end", headers=tutor["headers"], json={"note": "Moving"})
    assert response.status_code == 200
    assert response.json()["end_date"] == booking["periods"][0]["ends_on"]
    assert helpers.lessons(client, parent)[0]["status"] == "confirmed"


def test_parents_see_when_the_tutor_is_busy_free_or_teaching(client, clock, paystack, parent, admin_headers):
    tutor = helpers.approved_tutor(client, admin_headers, windows=[
        {"day_of_week": d, "start_time": "14:00", "end_time": "18:00"} for d in range(7)])
    helpers.paid_booking(client, paystack, parent, tutor)  # 15:00-16:00 on the lesson's weekday
    day = helpers.days_ahead(3).weekday()

    schedule = client.get(f"/v1/tutors/{tutor['id']}/schedule").json()  # public, no login needed
    assert schedule["busy"] == [{"day_of_week": day, "start_time": "15:00:00", "end_time": "16:00:00"}]
    free_that_day = [(f["start_time"], f["end_time"]) for f in schedule["free"] if f["day_of_week"] == day]
    assert free_that_day == [("14:00:00", "15:00:00"), ("16:00:00", "18:00:00")]
    assert len(schedule["free"]) == 8  # 6 untouched days + the 2 pieces left on the booked day
    assert "parent" not in str(schedule)
    assert schedule["in_session_now"] is False

    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["starts_at"]) + timedelta(minutes=10))
    assert client.get(f"/v1/tutors/{tutor['id']}/schedule").json()["in_session_now"] is True
