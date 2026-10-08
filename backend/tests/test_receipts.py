"""Receipts: parents for every movement of their money, tutors for every payout."""

import pytest

from tests import helpers


@pytest.fixture
def parent(client):
    return helpers.register_parent(client, full_name="Ada Okafor")


@pytest.fixture
def tutor(client, admin_headers, paystack):
    paystack.account_names["0123456789"] = "TUTOR TUNDE"
    return helpers.approved_tutor(client, admin_headers)


def entries(client, parent) -> list[dict]:
    return client.get("/v1/wallet/me", headers=parent["headers"]).json()["entries"]


def test_parent_gets_receipts_for_the_transfer_and_the_lessons_it_paid(client, paystack, parent, tutor):
    helpers.paid_booking(client, paystack, parent, tutor)
    payment, deposit = entries(client, parent)

    received = client.get(f"/v1/wallet/me/receipts/{deposit['id']}", headers=parent["headers"]).json()
    assert received["title"] == "Payment received" and received["total"] == "5500.00"
    assert received["receipt_number"].startswith("TL-") and received["parent_name"] == "Ada Okafor"

    paid = client.get(f"/v1/wallet/me/receipts/{payment['id']}", headers=parent["headers"]).json()
    assert paid["title"] == "Lessons paid" and paid["total"] == "5500.00" and paid["balance_after"] == "0.00"
    assert len(paid["lines"]) == 1
    assert "Mathematics with Tunde Tutor" in paid["lines"][0]["description"]
    assert paid["lines"][0]["amount"] == "5500.00"
    # The parent's receipt never shows the fee rate or the tutor's earning.
    text = str(paid)
    assert "4600" not in text and "0.10" not in text and "fee" not in text.lower()


def test_payment_notifications_link_to_the_receipt(client, paystack, parent, tutor):
    helpers.paid_booking(client, paystack, parent, tutor)
    links = [n["link"] for n in client.get("/v1/notifications/me", headers=parent["headers"]).json()["items"]]
    assert sum(1 for link in links if link and link.startswith("/receipts/wallet/")) == 2


def test_a_parent_cannot_open_another_parents_receipt(client, paystack, parent, tutor):
    helpers.paid_booking(client, paystack, parent, tutor)
    entry = entries(client, parent)[0]
    other = helpers.register_parent(client)
    assert client.get(f"/v1/wallet/me/receipts/{entry['id']}", headers=other["headers"]).status_code == 404


def test_tutor_gets_a_payout_receipt_with_price_fee_and_earning(client, db, clock, paystack, parent, tutor,
                                                                admin_headers):
    client.put("/v1/earnings/me/bank-account", headers=tutor["headers"],
               json={"bank_code": "044", "account_number": "0123456789"})
    helpers.completed_lesson(client, db, clock, paystack, parent, tutor)
    payout = client.post("/v1/admin/payouts", headers=admin_headers,
                         json={"tutor_id": tutor["id"], "method": "paystack"}).json()
    helpers.transfer_event(client, payout["reference"])

    mine = client.get("/v1/earnings/me/payouts", headers=tutor["headers"]).json()
    assert [p["status"] for p in mine] == ["paid"]
    receipt = client.get(f"/v1/earnings/payouts/{payout['id']}/receipt", headers=tutor["headers"]).json()
    assert receipt["total_price"] == "5000.00" and receipt["total_fee"] == "400.00" and receipt["total"] == "4600.00"
    assert receipt["tutor_fee_rate"] == "0.0800" and receipt["bank"] == "Access Bank ****6789"
    line = receipt["lines"][0]
    assert line["parent_first_name"] == "Ada" and line["subjects"] == ["Mathematics"]
    # The tutor's receipt never shows what the parent paid.
    assert "5500" not in str(receipt) and "Okafor" not in str(receipt)

    titles = {n["title"]: n["link"] for n in client.get("/v1/notifications/me", headers=tutor["headers"]).json()["items"]}
    assert titles["You've been paid"] == f"/receipts/payouts/{payout['id']}"


def test_a_tutor_cannot_open_another_tutors_payout_receipt(client, db, clock, paystack, parent, tutor,
                                                           admin_headers):
    helpers.completed_lesson(client, db, clock, paystack, parent, tutor)
    payout = client.post("/v1/admin/payouts", headers=admin_headers,
                         json={"tutor_id": tutor["id"], "method": "manual"}).json()
    other = helpers.approved_tutor(client, admin_headers)
    assert client.get(f"/v1/earnings/payouts/{payout['id']}/receipt", headers=other["headers"]).status_code == 404
    assert client.get(f"/v1/earnings/payouts/{payout['id']}/receipt", headers=admin_headers).status_code == 200
