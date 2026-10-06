"""Each email trigger in CLAUDE.md sends the right subject to the right people."""

from app.domains.notifications import service as notifications
from tests import helpers


def sent_to(outbox, email: str) -> list[str]:
    return [e["subject"] for e in outbox if e["to"] == email]


def test_tutor_registration_and_vetting_emails(client, admin_headers, outbox):
    approved = helpers.register_tutor(client)
    rejected = helpers.register_tutor(client)
    helpers.vet(client, admin_headers, approved, "approved")
    helpers.vet(client, admin_headers, rejected, "rejected", note="Missing documents")

    assert sent_to(outbox, approved["email"]) == ["We received your application",
                                                  "You're approved! Welcome to TutorLink"]
    assert sent_to(outbox, rejected["email"]) == ["We received your application",
                                                  "Update on your TutorLink application"]
    assert "Missing documents" in outbox[-1]["html"]


def test_parent_registration_sends_no_email(client, outbox):
    parent = helpers.register_parent(client)
    assert sent_to(outbox, parent["email"]) == []


def test_schedule_booked_and_cancelled_emails_go_to_both(client, admin_headers, outbox):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    schedule = helpers.booked_schedule(client, parent, tutor, day=2)
    client.delete(f"/v1/schedules/{schedule['id']}", headers=parent["headers"])

    for email in (parent["email"], tutor["email"]):
        subjects = sent_to(outbox, email)
        assert "New session booked: Mathematics every Wednesday" in subjects
        assert "Session cancelled" in subjects


def test_session_logged_email_to_parent(client, admin_headers, outbox):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    schedule = helpers.booked_schedule(client, parent, tutor)
    helpers.logged_session(client, tutor, schedule["id"], "2025-10-06")
    assert "Please confirm your Mathematics session on Monday 6 October 2025" in sent_to(outbox, parent["email"])


def test_invoice_generated_email_to_parent(client, admin_headers, outbox):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    schedule = helpers.booked_schedule(client, parent, tutor)
    helpers.confirmed_session(client, parent, tutor, schedule["id"], "2025-10-06")
    client.post("/v1/invoices/generate", headers=admin_headers, json={"month": 10, "year": 2025})
    assert "Your TutorLink invoice for October 2025 is ready" in sent_to(outbox, parent["email"])


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
