"""Spec 1 R2.6-R3: paying upfront by bank transfer, the balance, deadlines, next periods, withdrawals."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.domains.payments.models import VirtualAccount
from tests import helpers


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers)


def wallet(client, parent) -> dict:
    return client.get("/v1/wallet/me", headers=parent["headers"]).json()


def booking_status(client, parent, booking) -> str:
    return client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["status"]


assert_ledger_matches = helpers.assert_ledger_matches


def test_full_flow_request_accept_transfer_pay_lessons(client, db, paystack, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    assert helpers.lessons(client, parent) == []  # nothing on the timetable until paid

    assert helpers.deposit(client, paystack, parent, "5500.00").json() == {"status": "ok"}

    assert booking_status(client, parent, booking) == "active"
    lessons = helpers.lessons(client, parent)
    assert len(lessons) == 1 and lessons[0]["status"] == "confirmed"
    assert lessons[0]["parent_price"] == "5500.00"
    w = wallet(client, parent)
    assert w["balance"] == "0.00" and w["amount_due"] == "0.00"
    assert [e["kind"] for e in w["entries"]] == ["period_payment", "deposit"]
    assert_ledger_matches(client, db, parent)
    tutor_lesson = helpers.lessons(client, tutor, "tutor")[0]
    assert tutor_lesson["tutor_earning"] == "4600.00" and "parent_price" not in tutor_lesson


def test_too_little_money_waits_and_a_top_up_pays(client, db, paystack, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    helpers.deposit(client, paystack, parent, "3000.00")
    assert booking_status(client, parent, booking) == "accepted"
    assert wallet(client, parent)["balance"] == "3000.00"
    helpers.deposit(client, paystack, parent, "3000.00")
    assert booking_status(client, parent, booking) == "active"
    assert wallet(client, parent)["balance"] == "500.00"
    assert_ledger_matches(client, db, parent)


def test_balance_already_there_pays_on_acceptance(client, paystack, parent, tutor):
    first = helpers.paid_booking(client, paystack, parent, tutor)
    helpers.deposit(client, paystack, parent, "6000.00")
    second = helpers.accepted_booking(client, parent, tutor, start_date=helpers.days_ahead(4))
    assert second["status"] == "active" and first["status"] == "active"


def test_unpaid_first_period_releases_the_booking_24_hours_before_the_lesson(client, db, clock, paystack,
                                                                               parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    due_at = datetime.fromisoformat(booking["periods"][0]["due_at"])
    clock.set(due_at - timedelta(minutes=1))
    helpers.run_jobs(db, clock)
    assert booking_status(client, parent, booking) == "accepted"
    clock.set(due_at + timedelta(minutes=1))
    helpers.run_jobs(db, clock)
    assert booking_status(client, parent, booking) == "released"
    # Paying late doesn't revive it; the money stays in the balance.
    helpers.deposit(client, paystack, parent, "5500.00")
    assert booking_status(client, parent, booking) == "released"
    assert wallet(client, parent)["balance"] == "5500.00"
    # The slot is free again.
    assert helpers.book(client, helpers.register_parent(client), tutor,
                        start_date=helpers.days_ahead(10, clock.now())).status_code == 201


def test_reminder_24_hours_before_the_deadline(client, db, clock, parent, tutor):
    booking = helpers.accepted_booking(client, parent, tutor)
    due_at = datetime.fromisoformat(booking["periods"][0]["due_at"])
    clock.set(due_at - timedelta(hours=23))
    helpers.run_jobs(db, clock)
    titles = [n["title"] for n in client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"]]
    assert "Payment due in 24 hours" in titles


def test_next_period_becomes_payable_when_the_current_one_starts(client, db, clock, paystack, parent, tutor):
    booking = helpers.paid_booking(client, paystack, parent, tutor)
    first = booking["periods"][0]
    clock.set(datetime.fromisoformat(first["due_at"]) + timedelta(days=1))  # first period has started
    helpers.run_jobs(db, clock)
    periods = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["periods"]
    assert len(periods) == 2 and periods[1]["status"] == "due"
    assert datetime.fromisoformat(periods[1]["due_at"]) > clock.now()

    helpers.deposit(client, paystack, parent, periods[1]["amount"])
    assert len(helpers.lessons(client, parent)) == 2


def test_missed_later_period_pauses_then_ends_after_7_days(client, db, clock, paystack, parent, tutor):
    booking = helpers.paid_booking(client, paystack, parent, tutor)
    clock.set(datetime.fromisoformat(booking["periods"][0]["due_at"]) + timedelta(days=1))
    helpers.run_jobs(db, clock)
    second = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()["periods"][1]
    clock.set(datetime.fromisoformat(second["due_at"]) + timedelta(minutes=1))
    helpers.run_jobs(db, clock)
    assert booking_status(client, parent, booking) == "paused"
    assert len(helpers.lessons(client, parent)) == 1  # the unpaid week isn't scheduled
    clock.travel(days=7, minutes=1)
    helpers.run_jobs(db, clock)
    assert booking_status(client, parent, booking) == "ended"


def test_daily_billing_charges_each_day_separately(client, paystack, parent, tutor):
    start = helpers.days_ahead(3)
    slots = [{"day_of_week": (start.weekday() + i) % 7, "start_time": "15:00", "end_time": "16:00"} for i in range(2)]
    booking = helpers.accepted_booking(client, parent, tutor, slots=slots, billing_period="daily")
    assert booking["periods"][0]["lesson_count"] == 1 and booking["periods"][0]["amount"] == "5500.00"


def test_monthly_billing_charges_the_rest_of_the_month(client, parent, tutor):
    start = helpers.days_ahead(3)
    booking = helpers.accepted_booking(client, parent, tutor, billing_period="monthly", start_date=start)
    period = booking["periods"][0]
    assert period["starts_on"] == start.isoformat()
    assert period["ends_on"][:7] == start.isoformat()[:7]  # same calendar month
    assert Decimal(period["amount"]) == Decimal("5500.00") * period["lesson_count"]


def test_end_date_limits_the_lessons(client, db, clock, paystack, parent, tutor):
    start = helpers.days_ahead(3)
    booking = helpers.paid_booking(client, paystack, parent, tutor, start_date=start, end_date=start)
    last = datetime.fromisoformat(helpers.lessons(client, parent)[0]["ends_at"])
    clock.set(last + timedelta(hours=1))
    helpers.run_jobs(db, clock)
    detail = client.get(f"/v1/bookings/{booking['id']}", headers=parent["headers"]).json()
    assert len(detail["periods"]) == 1 and detail["status"] == "ended"


# ---------- Withdrawals ----------

def test_withdrawal_takes_from_balance_and_admin_sends_it(client, db, paystack, parent, admin_headers):
    helpers.accepted_booking(client, parent, helpers.approved_tutor(client, admin_headers))
    helpers.deposit(client, paystack, parent, "10000.00")  # 5,500 pays the lesson, 4,500 left
    paystack.account_names["0123456789"] = "ADA PARENT"
    response = client.post("/v1/wallet/me/withdrawals", headers=parent["headers"],
                           json={"amount": "4500.00", "bank_code": "044", "account_number": "0123456789"})
    assert response.status_code == 201 and response.json()["account_name"] == "ADA PARENT"
    assert wallet(client, parent)["balance"] == "0.00"

    withdrawal = client.get("/v1/admin/withdrawals", headers=admin_headers).json()[0]
    sent = client.post(f"/v1/admin/withdrawals/{withdrawal['id']}/send", headers=admin_headers)
    assert sent.json()["status"] == "processing"
    assert paystack.transfers[-1]["amount_kobo"] == 450000
    helpers.transfer_event(client, withdrawal["reference"], "transfer.success")
    assert client.get("/v1/wallet/me/withdrawals", headers=parent["headers"]).json()[0]["status"] == "paid"
    assert_ledger_matches(client, db, parent)


def test_withdrawal_cannot_exceed_balance(client, paystack, parent):
    response = client.post("/v1/wallet/me/withdrawals", headers=parent["headers"],
                           json={"amount": "1.00", "bank_code": "044", "account_number": "0123456789"})
    assert response.status_code == 409


def test_failed_or_rejected_withdrawal_returns_the_money(client, db, paystack, parent, tutor, admin_headers):
    helpers.accepted_booking(client, parent, tutor)
    helpers.deposit(client, paystack, parent, "7500.00")  # 2,000 left after the lesson
    for _ in range(2):
        client.post("/v1/wallet/me/withdrawals", headers=parent["headers"],
                    json={"amount": "1000.00", "bank_code": "044", "account_number": "0123456789"})
    first, second = client.get("/v1/admin/withdrawals", headers=admin_headers).json()
    client.post(f"/v1/admin/withdrawals/{first['id']}/reject", headers=admin_headers, json={"note": "Wrong bank"})
    client.post(f"/v1/admin/withdrawals/{second['id']}/send", headers=admin_headers)
    helpers.transfer_event(client, second["reference"], "transfer.failed")
    assert wallet(client, parent)["balance"] == "2000.00"
    assert_ledger_matches(client, db, parent)


def test_withdrawals_are_admin_only(client, parent):
    assert client.get("/v1/admin/withdrawals", headers=parent["headers"]).status_code == 403


def test_banks_list(client, parent):
    banks = client.get("/v1/banks", headers=parent["headers"]).json()
    assert {"name": "Access Bank", "code": "044"} in banks


def test_account_number_on_request_when_not_yet_created(client, parent):
    response = client.post("/v1/wallet/me/account-number", headers=parent["headers"])
    assert response.status_code == 200 and response.json()["bank_name"] == "Test Bank"
    assert wallet(client, parent)["virtual_account"]["account_number"] == response.json()["account_number"]


def test_no_two_parents_share_an_account_number(client, db, paystack, parent):
    """Spec 1 R3.1: each parent's account number is theirs alone, and the database refuses a repeat."""
    other = helpers.register_parent(client)
    numbers = [client.post("/v1/wallet/me/account-number", headers=p["headers"]).json()["account_number"]
               for p in (parent, other)]
    assert numbers[0] != numbers[1]
    third = helpers.register_parent(client)
    db.add(VirtualAccount(parent_id=third["id"], customer_code="CUS_REPEAT", account_number=numbers[0],
                          account_name="TUTORLINK/PARENT", bank_name="Test Bank"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
