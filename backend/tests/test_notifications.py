"""Each email trigger in CLAUDE.md sends the right subject to the right people."""

from app.domains.notifications import service as notifications
from tests import helpers


def sent_to(outbox, email: str) -> list[str]:
    return [e["subject"] for e in outbox if e["to"] == email]


def test_tutor_registration_and_vetting_emails(client, admin_headers, outbox):
    approved = helpers.certified_tutor(client, admin_headers)
    rejected = helpers.register_tutor(client)
    helpers.vet(client, admin_headers, approved, "approved")
    helpers.vet(client, admin_headers, rejected, "rejected", note="Missing documents")

    assert sent_to(outbox, approved["email"]) == ["We received your application",
                                                  "Your Degree certificate is verified",
                                                  "You're approved! Welcome to TutorLink"]
    assert sent_to(outbox, rejected["email"]) == ["We received your application",
                                                  "Update on your TutorLink application"]
    assert "Missing documents" in outbox[-1]["html"]


def test_parent_registration_sends_no_email(client, outbox):
    parent = helpers.register_parent(client)
    assert sent_to(outbox, parent["email"]) == []


def test_booking_events_reach_both_sides_in_app_and_by_email(client, admin_headers, paystack, outbox):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    helpers.paid_booking(client, paystack, parent, tutor)

    assert sent_to(outbox, tutor["email"])[-2:] == ["New booking request", "Lessons confirmed"]
    assert sent_to(outbox, parent["email"]) == ["Your booking has been taken", "Payment received — thank you!",
                                                "Lessons confirmed"]
    in_app = client.get("/v1/notifications/me", headers=parent["headers"]).json()
    assert in_app["unread_count"] == 3
    assert [n["title"] for n in in_app["items"]][0] == "Lessons confirmed"  # newest first


def test_marking_notifications_read(client, admin_headers):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    helpers.requested_booking(client, parent, tutor)
    helpers.requested_booking(client, helpers.register_parent(client), tutor, start_date=helpers.days_ahead(4))
    mine = client.get("/v1/notifications/me", headers=tutor["headers"]).json()
    items = mine["items"]
    assert client.post(f"/v1/notifications/{items[0]['id']}/read", headers=tutor["headers"]).status_code == 204
    assert client.get("/v1/notifications/me", headers=tutor["headers"]).json()["unread_count"] == mine["unread_count"] - 1
    client.post("/v1/notifications/me/read-all", headers=tutor["headers"])
    assert client.get("/v1/notifications/me", headers=tutor["headers"]).json()["unread_count"] == 0
    # Someone else's notification can't be touched.
    client.post(f"/v1/notifications/{items[1]['id']}/read", headers=parent["headers"])


def test_no_email_when_the_change_is_rolled_back(db, outbox):
    parent_id = helpers_user(db)
    notifications.notify(db, parent_id, "Should not send", "Rolled back")
    db.rollback()
    db.commit()
    assert outbox == []


def helpers_user(db):
    from app.domains.auth.models import User, UserRole

    user = User(email=helpers.unique_email("x"), password_hash="x", role=UserRole.parent)
    db.add(user)
    db.commit()
    return user.id


def test_user_supplied_text_is_html_escaped(client, admin_headers, outbox):
    tutor = helpers.register_tutor(client)
    helpers.vet(client, admin_headers, tutor, "rejected", note="<script>alert(1)</script>")
    assert "<script>" not in outbox[-1]["html"]


def test_send_email_without_resend_key_only_logs(monkeypatch, caplog):
    # The autouse outbox fixture replaced send_email; test the real one directly.
    monkeypatch.undo()
    monkeypatch.setattr(notifications.settings, "RESEND_API_KEY", "re_xxxxxxxx")
    with caplog.at_level("INFO"):
        notifications.send_email("someone@example.com", "Hello", "<p>Hi</p>")
    assert "Resend not configured" in caplog.text
