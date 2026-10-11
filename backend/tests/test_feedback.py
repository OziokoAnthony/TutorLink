"""Spec 6: feedback from parents and tutors, admin replies, and the help assistant."""

import pytest

from app.core import claude as claude_client
from tests import helpers

MESSAGE = "The lessons page takes a long time to load."


def send(client, user: dict, kind: str = "problem", message: str = MESSAGE, **extra):
    return client.post("/v1/feedback", json={"kind": kind, "message": message, **extra}, headers=user["headers"])


def waiting(client, admin_headers: dict, answered: bool = False) -> list[dict]:
    response = client.get(f"/v1/admin/feedback?answered={str(answered).lower()}", headers=admin_headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_parent_and_tutor_send_feedback_and_see_it(client):
    """R1.1, R1.2."""
    parent = helpers.register_parent(client)
    tutor = helpers.register_tutor(client)
    assert send(client, parent).status_code == 201
    assert send(client, parent, kind="praise", message="Our tutor is wonderful, thank you!").status_code == 201
    assert send(client, tutor, kind="suggestion", message="Let me add more than one level per offer.").status_code == 201

    mine = client.get("/v1/feedback/me", headers=parent["headers"]).json()
    assert [f["kind"] for f in mine] == ["praise", "problem"]  # newest first
    assert mine[1]["message"] == MESSAGE and mine[1]["reply"] is None
    assert len(client.get("/v1/feedback/me", headers=tutor["headers"]).json()) == 1


@pytest.mark.parametrize("message", ["Too short", "x" * 2001])
def test_message_length(client, message):
    """R1.1: 10-2,000 characters."""
    assert send(client, helpers.register_parent(client), message=message).status_code == 422


def test_admins_and_visitors_cant_send(client, admin_headers):
    """R1.4."""
    assert send(client, {"headers": admin_headers}).status_code == 403
    assert client.post("/v1/feedback", json={"kind": "problem", "message": MESSAGE}).status_code == 401


def test_admins_are_told_in_the_app(client, admin_headers, outbox):
    """R2.2: an in-app notification, no email."""
    send(client, helpers.register_parent(client))
    titles = [n["title"] for n in client.get("/v1/notifications/me", headers=admin_headers).json()["items"]]
    assert "New feedback" in titles
    assert not [e for e in outbox if e["subject"] == "New feedback"]


def test_admin_lists_and_replies_once(client, admin_headers, outbox):
    """R2.1, R2.3."""
    parent = helpers.register_parent(client, full_name="Ada Okafor")
    first = send(client, parent).json()
    second = send(client, parent, kind="question", message="How do I withdraw my balance?").json()

    queue = waiting(client, admin_headers)
    assert [f["id"] for f in queue] == [first["id"], second["id"]]  # oldest first
    assert queue[0]["user_name"] == "Ada Okafor"
    assert queue[0]["user_email"] == parent["email"] and queue[0]["user_role"] == "parent"

    reply = "Thanks, we've found the slow page and are fixing it."
    response = client.post(f"/v1/admin/feedback/{first['id']}/reply", json={"reply": reply}, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["reply"] == reply

    assert [f["id"] for f in waiting(client, admin_headers)] == [second["id"]]
    assert [f["id"] for f in waiting(client, admin_headers, answered=True)] == [first["id"]]
    mine = client.get("/v1/feedback/me", headers=parent["headers"]).json()
    assert next(f for f in mine if f["id"] == first["id"])["reply"] == reply
    email = next(e for e in outbox if e["subject"] == "TutorLink replied to your feedback")
    assert email["to"] == parent["email"] and "fixing it" in email["html"]

    again = client.post(f"/v1/admin/feedback/{first['id']}/reply", json={"reply": "Again"}, headers=admin_headers)
    assert again.status_code == 409


def test_only_admins_list_and_reply(client):
    parent = helpers.register_parent(client)
    feedback = send(client, parent).json()
    assert client.get("/v1/admin/feedback", headers=parent["headers"]).status_code == 403
    response = client.post(f"/v1/admin/feedback/{feedback['id']}/reply", json={"reply": "Hello"},
                           headers=parent["headers"])
    assert response.status_code == 403


# ---------- Help assistant (R3) ----------

@pytest.fixture
def assistant(monkeypatch):
    """A fake help assistant that records what it was asked."""
    calls: list[tuple[str, list[dict]]] = []

    def help_reply(role, messages):
        calls.append((role, messages))
        return f"Answer for a {role}."

    monkeypatch.setattr(claude_client, "available", lambda: True)
    monkeypatch.setattr(claude_client, "help_reply", help_reply)
    return calls


def chat(client, user: dict, *messages: tuple[str, str]):
    return client.post("/v1/help/chat", json={"messages": [{"role": r, "content": c} for r, c in messages]},
                       headers=user["headers"])


def test_help_chat_answers_for_the_readers_role(client, assistant):
    """R3.1."""
    tutor = helpers.register_tutor(client)
    response = chat(client, tutor, ("user", "How do I pass the quiz?"), ("assistant", "Study."),
                    ("user", "How many attempts do I get?"))
    assert response.status_code == 200, response.text
    assert response.json() == {"reply": "Answer for a tutor."}
    role, messages = assistant[0]
    assert role == "tutor" and [m["role"] for m in messages] == ["user", "assistant", "user"]


def test_help_chat_must_end_with_the_user(client, assistant):
    parent = helpers.register_parent(client)
    assert chat(client, parent, ("user", "Hi"), ("assistant", "Hello")).status_code == 422
    assert chat(client, parent, ("assistant", "Hello"), ("user", "Hi")).status_code == 422
    assert not assistant


def test_help_chat_unavailable(client, monkeypatch):
    """R3.6: without a key, or when Claude gives no answer, it's a 503."""
    parent = helpers.register_parent(client)
    monkeypatch.setattr(claude_client, "available", lambda: False)
    assert chat(client, parent, ("user", "Hi")).status_code == 503
    monkeypatch.setattr(claude_client, "available", lambda: True)
    monkeypatch.setattr(claude_client, "help_reply", lambda role, messages: None)
    assert chat(client, parent, ("user", "Hi")).status_code == 503


def test_help_chat_is_for_parents_and_tutors(client, admin_headers, assistant):
    assert chat(client, {"headers": admin_headers}, ("user", "Hi")).status_code == 403


def test_conversation_sent_to_the_team(client, admin_headers):
    """R3.4: it arrives as a question with the conversation attached."""
    parent = helpers.register_parent(client)
    transcript = [{"role": "user", "content": "My deposit isn't showing."},
                  {"role": "assistant", "content": "I can't see your account; please send this to the team."}]
    response = send(client, parent, kind="question", message="My deposit isn't showing.", transcript=transcript)
    assert response.status_code == 201, response.text
    assert waiting(client, admin_headers)[0]["transcript"] == transcript
