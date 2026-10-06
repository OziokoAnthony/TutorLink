from decimal import Decimal

import pytest

from tests import helpers


def generate(client, admin_headers, month=10, year=2025):
    response = client.post("/v1/invoices/generate", headers=admin_headers, json={"month": month, "year": year})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def parent(client):
    return helpers.register_parent(client)


@pytest.fixture
def tutor(client, admin_headers):
    return helpers.approved_tutor(client, admin_headers, rate="5000.00")


@pytest.fixture
def schedule(client, parent, tutor):
    return helpers.booked_schedule(client, parent, tutor)


def test_only_confirmed_sessions_are_invoiced(client, admin_headers, parent, tutor, schedule):
    wednesday_schedule = helpers.booked_schedule(client, parent, tutor, day=2)
    helpers.confirmed_session(client, parent, tutor, wednesday_schedule["id"], "2025-10-01")
    for day in ("2025-10-06", "2025-10-13"):  # Mondays, matching `schedule`
        helpers.confirmed_session(client, parent, tutor, schedule["id"], day)
    helpers.logged_session(client, tutor, schedule["id"], "2025-10-20")
    cancelled = helpers.logged_session(client, tutor, schedule["id"], "2025-10-27")
    client.patch(f"/v1/sessions/{cancelled['id']}/cancel", headers=parent["headers"])

    result = generate(client, admin_headers)
    assert result["created"] == 1
    invoice = client.get(f"/v1/invoices/{result['invoices'][0]['id']}", headers=parent["headers"]).json()
    assert invoice["total_sessions"] == 3
    assert len(invoice["items"]) == 3


def test_generating_twice_skips_existing_invoice(client, admin_headers, parent, tutor, schedule):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    assert generate(client, admin_headers)["created"] == 1
    second = generate(client, admin_headers)
    assert second["created"] == 0
    assert second["skipped_existing"] == 1
    assert len(client.get("/v1/invoices/me", headers=parent["headers"]).json()) == 1


def test_invoice_total_is_sum_of_tutor_rates_and_commission_stored(client, admin_headers, parent, tutor, schedule):
    other_tutor = helpers.approved_tutor(client, admin_headers, rate="7500.50")
    other_schedule = helpers.booked_schedule(client, parent, other_tutor, day=2)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-13")
    helpers.confirmed_session(client, parent, other_tutor, other_schedule["id"], "2025-10-08")

    invoice = generate(client, admin_headers)["invoices"][0]
    expected_subtotal = Decimal("5000.00") * 2 + Decimal("7500.50")
    assert Decimal(invoice["subtotal"]) == expected_subtotal
    assert Decimal(invoice["total_amount"]) == expected_subtotal
    assert Decimal(invoice["commission_rate"]) == Decimal("0.1000")
    assert Decimal(invoice["commission_amount"]) == Decimal("1750.05")
    assert invoice["status"] == "pending"


def test_commission_is_not_recalculated_when_rate_changes_later(client, admin_headers, parent, tutor, schedule):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    invoice_id = generate(client, admin_headers)["invoices"][0]["id"]
    client.post("/v1/tutors/profile", headers=tutor["headers"], json={
        "full_name": "Tunde Tutor", "area": "Lekki", "rate_per_session": "9999.00",
    })
    invoice = client.get(f"/v1/invoices/{invoice_id}", headers=parent["headers"]).json()
    assert Decimal(invoice["subtotal"]) == Decimal("5000.00")
    assert Decimal(invoice["items"][0]["amount"]) == Decimal("5000.00")


def test_sessions_outside_the_month_are_excluded(client, admin_headers, parent, tutor, schedule):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-09-29")
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-11-03")
    assert generate(client, admin_headers)["created"] == 0


def test_one_invoice_per_parent(client, admin_headers, parent, tutor, schedule):
    other_parent = helpers.register_parent(client)
    other_schedule = helpers.booked_schedule(client, other_parent, tutor, day=3)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    helpers.confirmed_session(client, other_parent, tutor, other_schedule["id"], "2025-10-09")
    assert generate(client, admin_headers)["created"] == 2


def test_generate_is_admin_only(client, parent):
    response = client.post("/v1/invoices/generate", headers=parent["headers"], json={"month": 10, "year": 2025})
    assert response.status_code == 403


def test_parent_cannot_view_another_parents_invoice(client, admin_headers, parent, tutor, schedule):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    invoice_id = generate(client, admin_headers)["invoices"][0]["id"]
    other_parent = helpers.register_parent(client)
    assert client.get(f"/v1/invoices/{invoice_id}", headers=other_parent["headers"]).status_code == 403
    assert client.post(f"/v1/invoices/{invoice_id}/pay", headers=other_parent["headers"]).status_code == 403


def test_pay_initializes_paystack_and_stores_reference(client, admin_headers, parent, tutor, schedule, paystack):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    invoice_id = generate(client, admin_headers)["invoices"][0]["id"]

    response = client.post(f"/v1/invoices/{invoice_id}/pay", headers=parent["headers"])
    assert response.status_code == 200
    reference = response.json()["reference"]
    assert response.json()["authorization_url"].endswith(reference)
    assert paystack[0]["amount_kobo"] == 500000
    assert paystack[0]["email"] == parent["email"]
    invoice = client.get(f"/v1/invoices/{invoice_id}", headers=parent["headers"]).json()
    assert invoice["paystack_reference"] == reference


def test_generate_reports_parent_names_and_parents_without_sessions(client, admin_headers, parent, tutor, schedule):
    helpers.register_parent(client)  # no sessions at all
    idle = helpers.register_parent(client)  # has a schedule but nothing confirmed
    helpers.booked_schedule(client, idle, tutor, day=4)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")

    result = generate(client, admin_headers)
    assert result["created"] == 1
    assert result["parents_without_sessions"] == 2
    assert result["invoices"][0]["parent_name"] == "Ada Parent"


def test_paystack_returns_parent_to_invoices_page(client, admin_headers, parent, tutor, schedule, paystack):
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    invoice_id = generate(client, admin_headers)["invoices"][0]["id"]
    client.post(f"/v1/invoices/{invoice_id}/pay", headers=parent["headers"])
    assert paystack[0]["callback_url"].endswith(f"/dashboard/parent/invoices?invoice={invoice_id}")
