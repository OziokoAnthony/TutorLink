"""Spec 1 R6: tutor bank details, what the admin owes each tutor, and payouts."""

from datetime import datetime, timedelta

import pytest

from tests import helpers

ACCOUNT = "0123456789"


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def tutor(client, admin_headers, paystack):
    tutor = helpers.approved_tutor(client, admin_headers, full_name="Tunde Bakare")
    paystack.account_names[ACCOUNT] = "BAKARE TUNDE"
    return tutor


def set_bank(client, tutor, account=ACCOUNT):
    return client.put("/v1/earnings/me/bank-account", headers=tutor["headers"],
                      json={"bank_code": "044", "account_number": account})


def payable_lesson(client, db, clock, paystack, parent, tutor) -> dict:
    return helpers.completed_lesson(client, db, clock, paystack, parent, tutor)


def test_bank_name_matching_any_order(client, tutor):
    response = set_bank(client, tutor)
    assert response.status_code == 200
    body = response.json()
    assert body["name_matches"] and body["approved_for_payouts"]
    assert body["account_last4"] == "6789" and "account_number" not in body


def test_mismatched_name_blocks_payouts_until_admin_overrides(client, paystack, tutor, admin_headers):
    paystack.account_names["1111111111"] = "SOMEONE ELSE"
    assert set_bank(client, tutor, "1111111111").json()["approved_for_payouts"] is False
    override = client.post(f"/v1/admin/tutors/{tutor['id']}/bank-account/override", headers=admin_headers,
                           json={"note": "Checked: account is in the tutor's married name"})
    assert override.status_code == 200
    assert client.get("/v1/earnings/me/bank-account", headers=tutor["headers"]).json()["approved_for_payouts"]


def test_only_admins_see_the_full_account_number(client, db, clock, paystack, parent, tutor, admin_headers):
    set_bank(client, tutor)
    payable_lesson(client, db, clock, paystack, parent, tutor)
    due = client.get("/v1/admin/payouts/due", headers=admin_headers).json()[0]
    assert due["bank_account"]["account_number"] == ACCOUNT
    assert client.get("/v1/admin/payouts/due", headers=tutor["headers"]).status_code == 403


def test_weekly_earnings_are_due_48_hours_after_the_weeks_last_lesson(client, db, clock, paystack, parent, tutor,
                                                                     admin_headers):
    """Spec 1 R6.2: a weekly booking with Monday and Wednesday lessons; both earnings are due 48 hours
    after Wednesday's lesson, not 48 hours after each one."""
    monday = helpers.days_ahead(3)
    monday += timedelta(days=-monday.weekday() % 7)
    slots = [{"day_of_week": day, "start_time": "15:00", "end_time": "16:00"} for day in (0, 2)]
    booking = helpers.paid_booking(client, paystack, parent, tutor, start_date=monday, slots=slots,
                                   billing_period="weekly")
    week = sorted((l for l in helpers.lessons(client, parent) if l["booking_id"] == booking["id"]),
                  key=lambda l: l["starts_at"])[:2]
    assert [datetime.fromisoformat(l["starts_at"]).weekday() for l in week] == [0, 2]
    for lesson in week:
        clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(minutes=5))
        assert helpers.report(client, tutor, lesson["id"]).status_code == 200
    clock.travel(hours=24, minutes=1)
    helpers.run_jobs(db, clock)

    due = client.get("/v1/admin/payouts/due", headers=admin_headers).json()
    assert len(due) == 1 and due[0]["lesson_count"] == 2 and due[0]["amount"] == "9200.00"
    last_ends = datetime.fromisoformat(week[-1]["ends_at"])
    assert datetime.fromisoformat(due[0]["due_at"]) == last_ends + timedelta(hours=48)


def test_payout_due_48_hours_after_the_periods_last_lesson(client, db, clock, paystack, parent, tutor, admin_headers):
    lesson = payable_lesson(client, db, clock, paystack, parent, tutor)
    due = client.get("/v1/admin/payouts/due", headers=admin_headers).json()
    assert len(due) == 1 and due[0]["amount"] == "4600.00" and due[0]["lesson_count"] == 1
    assert datetime.fromisoformat(due[0]["due_at"]) == datetime.fromisoformat(lesson["ends_at"]) + timedelta(hours=48)


def test_paystack_payout_pays_each_earning_once(client, db, clock, paystack, parent, tutor, admin_headers):
    set_bank(client, tutor)
    payable_lesson(client, db, clock, paystack, parent, tutor)
    response = client.post("/v1/admin/payouts", headers=admin_headers,
                           json={"tutor_id": tutor["id"], "method": "paystack"})
    assert response.status_code == 201
    payout = response.json()
    assert payout["status"] == "processing" and payout["amount"] == "4600.00"
    assert paystack.transfers[-1]["amount_kobo"] == 460000
    assert client.post("/v1/admin/payouts", headers=admin_headers,
                       json={"tutor_id": tutor["id"], "method": "paystack"}).status_code == 409

    helpers.transfer_event(client, payout["reference"], "transfer.success")
    assert client.get("/v1/admin/payouts", headers=admin_headers).json()[0]["status"] == "paid"
    assert client.get("/v1/earnings/me", headers=tutor["headers"]).json()["paid"] == "4600.00"


def test_failed_transfer_makes_earnings_payable_again(client, db, clock, paystack, parent, tutor, admin_headers):
    set_bank(client, tutor)
    payable_lesson(client, db, clock, paystack, parent, tutor)
    payout = client.post("/v1/admin/payouts", headers=admin_headers,
                         json={"tutor_id": tutor["id"], "method": "paystack"}).json()
    helpers.transfer_event(client, payout["reference"], "transfer.failed")
    assert client.get("/v1/earnings/me", headers=tutor["headers"]).json()["payable"] == "4600.00"
    assert len(client.get("/v1/admin/payouts/due", headers=admin_headers).json()) == 1


def test_manual_payout_is_paid_at_once(client, db, clock, paystack, parent, tutor, admin_headers):
    payable_lesson(client, db, clock, paystack, parent, tutor)
    response = client.post("/v1/admin/payouts", headers=admin_headers,
                           json={"tutor_id": tutor["id"], "method": "manual", "note": "GTB transfer 4471"})
    assert response.json()["status"] == "paid"
    assert client.get("/v1/admin/payouts/due", headers=admin_headers).json() == []


def test_paystack_payout_needs_cleared_bank_details(client, db, clock, paystack, parent, tutor, admin_headers):
    payable_lesson(client, db, clock, paystack, parent, tutor)
    response = client.post("/v1/admin/payouts", headers=admin_headers,
                           json={"tutor_id": tutor["id"], "method": "paystack"})
    assert response.status_code == 409


def test_earnings_on_hold_are_never_payable(client, clock, paystack, parent, tutor, admin_headers):
    helpers.paid_booking(client, paystack, parent, tutor)
    lesson = helpers.lessons(client, parent)[0]
    clock.set(datetime.fromisoformat(lesson["ends_at"]) + timedelta(hours=1))
    client.post(f"/v1/lessons/{lesson['id']}/problem", headers=parent["headers"],
                json={"kind": "tutor_absent", "description": "Nobody came to the house."})
    assert client.get("/v1/admin/payouts/due", headers=admin_headers).json() == []
    assert client.get("/v1/earnings/me", headers=tutor["headers"]).json()["on_hold"] == "4600.00"
