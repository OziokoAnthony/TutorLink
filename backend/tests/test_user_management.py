"""Spec 10: parents and tutors at a glance, and removing accounts with notice."""

from datetime import timedelta

from sqlmodel import select

from app.domains.auth.models import User
from app.domains.job_posts.models import JobPost
from tests import helpers

REASON = "You haven't used TutorLink for over six months."


def _row(client, admin_headers, user_id: str) -> dict:
    rows = client.get("/v1/admin/users", headers=admin_headers, params={"limit": 200}).json()
    return next(r for r in rows if r["id"] == user_id)


def _notice(client, admin_headers, user: dict, reason: str = REASON):
    return client.post(f"/v1/admin/users/{user['id']}/notice", headers=admin_headers, json={"reason": reason})


def _remove(client, admin_headers, user: dict):
    return client.post(f"/v1/admin/users/{user['id']}/remove", headers=admin_headers)


def _titles(client, user) -> list[str]:
    return [n["title"] for n in client.get("/v1/notifications/me", headers=user["headers"]).json()["items"]]


# ---------- R1: last seen ----------

def test_last_seen_is_recorded_at_most_once_an_hour(client, db, admin_headers, clock):
    parent = helpers.register_parent(client)  # logged in by the helper
    first = db.get(User, parent["id"]).last_seen_at
    assert first is not None

    clock.travel(minutes=30)
    client.get("/v1/auth/me", headers=parent["headers"])
    db.expire_all()
    assert db.get(User, parent["id"]).last_seen_at == first  # within the hour: no write

    clock.travel(minutes=31)
    client.get("/v1/auth/me", headers=parent["headers"])
    db.expire_all()
    assert db.get(User, parent["id"]).last_seen_at > first


# ---------- R2, R3: bands, counts and the list ----------

def test_the_overview_counts_by_role_band_and_onboarding_stage(client, admin_headers, clock):
    helpers.register_parent(client)
    helpers.register_tutor(client)
    clock.travel(days=100)
    helpers.register_parent(client)  # seen today
    clock.travel(days=100)  # first parent: 200 days; second: 100 days; tutor: 200 days

    overview = client.get("/v1/admin/users/overview", headers=admin_headers).json()
    assert overview["parents"] == {"registered": 2, "active": 0, "inactive": 1, "long_inactive": 1,
                                   "notice": 0, "removed": 0}
    assert overview["tutors"]["registered"] == 1 and overview["tutors"]["long_inactive"] == 1
    assert overview["tutor_stages"] == {"onboarding": 1, "approved": 0, "rejected": 0}


def test_the_list_filters_and_shows_what_is_outstanding(client, admin_headers, paystack, claude):
    parent = helpers.register_parent(client, full_name="Ada Okafor")
    tutor = helpers.approved_tutor(client, admin_headers)
    helpers.paid_booking(client, paystack, parent, tutor)
    helpers.deposit(client, paystack, parent, "20000.00")

    rows = client.get("/v1/admin/users", headers=admin_headers, params={"role": "parent"}).json()
    assert [r["email"] for r in rows] == [parent["email"]]
    ada = rows[0]
    assert ada["name"] == "Ada Okafor" and ada["band"] == "active" and ada["last_seen_at"]
    assert ada["outstanding"] == ["₦20,000.00 balance", "1 unfinished booking"]

    tutors = client.get("/v1/admin/users", headers=admin_headers, params={"vetting": "approved"}).json()
    assert [r["id"] for r in tutors] == [tutor["id"]]
    assert any(o.endswith("not paid yet") for o in tutors[0]["outstanding"])
    assert any(o.endswith("not finished") for o in tutors[0]["outstanding"])

    found = client.get("/v1/admin/users", headers=admin_headers, params={"q": "okafor"}).json()
    assert [r["id"] for r in found] == [parent["id"]]
    assert client.get("/v1/admin/users", headers=admin_headers, params={"band": "long_inactive"}).json() == []


# ---------- R4, R5: notice ----------

def test_no_notice_while_something_is_outstanding(client, admin_headers, paystack, claude):
    parent = helpers.register_parent(client)
    tutor = helpers.approved_tutor(client, admin_headers)
    helpers.paid_booking(client, paystack, parent, tutor)
    for user in (parent, tutor):
        refused = _notice(client, admin_headers, user)
        assert refused.status_code == 409 and "can't be removed while it has" in refused.json()["detail"]
    assert "unfinished booking" in _notice(client, admin_headers, parent).json()["detail"]


def test_a_notice_tells_the_person_and_can_be_cancelled(client, admin_headers, outbox):
    parent = helpers.register_parent(client)
    sent = _notice(client, admin_headers, parent)
    assert sent.status_code == 200, sent.text
    row = sent.json()
    assert row["band"] == "notice" and row["removal_reason"] == REASON and not row["ready_to_remove"]

    assert "Your TutorLink account will be closed" in _titles(client, parent)
    assert any(m["to"] == parent["email"] and "will be closed" in m["subject"] for m in outbox)
    me = client.get("/v1/auth/me", headers=parent["headers"]).json()["user"]
    assert me["removal_reason"] == REASON and me["removal_due_at"] == row["removal_due_at"]  # the banner (R5.2)
    assert _notice(client, admin_headers, parent).status_code == 409  # already running

    cancelled = client.delete(f"/v1/admin/users/{parent['id']}/notice", headers=admin_headers)
    assert cancelled.status_code == 200 and cancelled.json()["band"] == "active"
    assert "Your TutorLink account will stay open" in _titles(client, parent)
    assert client.get("/v1/auth/me", headers=parent["headers"]).json()["user"]["removal_due_at"] is None


def test_a_reason_is_required(client, admin_headers):
    parent = helpers.register_parent(client)
    assert _notice(client, admin_headers, parent, reason="Too short").status_code == 422


# ---------- R6: removing and restoring ----------

def test_removing_waits_for_the_notice_then_closes_the_account(client, db, admin_headers, clock, outbox):
    parent = helpers.register_parent(client)
    job = helpers.submit_job(client, parent)
    assert _remove(client, admin_headers, parent).status_code == 409  # no notice yet
    _notice(client, admin_headers, parent)
    clock.travel(days=13)
    early = _remove(client, admin_headers, parent)
    assert early.status_code == 409 and "notice runs until" in early.json()["detail"]

    clock.travel(days=1, minutes=1)
    assert _row(client, admin_headers, parent["id"])["ready_to_remove"] is True
    removed = _remove(client, admin_headers, parent)
    assert removed.status_code == 200 and removed.json()["band"] == "removed"

    assert client.get("/v1/auth/me", headers=parent["headers"]).status_code == 401  # sessions ended
    assert client.post("/v1/auth/login", json={"email": parent["email"], "password": helpers.PASSWORD}).status_code == 401
    assert db.exec(select(JobPost.status).where(JobPost.id == job["id"])).one() == "closed"
    assert any(m["to"] == parent["email"] and "has been closed" in m["subject"] for m in outbox)

    restored = client.post(f"/v1/admin/users/{parent['id']}/restore", headers=admin_headers)
    assert restored.status_code == 200 and restored.json()["band"] == "active"
    helpers.login(client, parent["email"])


def test_a_removed_tutor_disappears_from_search(client, admin_headers, clock, claude):
    tutor = helpers.approved_tutor(client, admin_headers)
    parent = helpers.register_parent(client)
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=parent["headers"]).status_code == 200
    _notice(client, admin_headers, tutor)
    clock.travel(days=15)
    assert _remove(client, admin_headers, tutor).status_code == 200
    parent_headers = helpers.login(client, parent["email"])
    assert client.get(f"/v1/tutors/{tutor['id']}", headers=parent_headers).status_code == 404
    assert tutor["id"] not in [t["id"] for t in client.get("/v1/tutors", headers=parent_headers).json()]


def test_something_outstanding_during_the_notice_blocks_removal(client, admin_headers, clock, paystack):
    parent = helpers.register_parent(client)
    assert client.post("/v1/wallet/me/account-number", headers=parent["headers"]).status_code == 200
    _notice(client, admin_headers, parent)
    clock.travel(days=15)
    helpers.deposit(client, paystack, parent, "5000.00")
    refused = _remove(client, admin_headers, parent)
    assert refused.status_code == 409 and "₦5,000.00 balance" in refused.json()["detail"]


def test_admins_are_not_listed_noticed_or_removed_here(client, db, admin_headers):
    admin_id = client.get("/v1/auth/me", headers=admin_headers).json()["user"]["id"]
    rows = client.get("/v1/admin/users", headers=admin_headers, params={"limit": 200}).json()
    assert admin_id not in [r["id"] for r in rows]
    assert _notice(client, admin_headers, {"id": admin_id}).status_code == 404
    parent = helpers.register_parent(client)
    assert client.get("/v1/admin/users", headers=parent["headers"]).status_code == 403


# ---------- R7: activity log ----------

def test_each_step_is_in_the_activity_log(client, admin_headers, clock):
    parent = helpers.register_parent(client, full_name="Ada Okafor")
    _notice(client, admin_headers, parent)
    client.delete(f"/v1/admin/users/{parent['id']}/notice", headers=admin_headers)
    _notice(client, admin_headers, parent)
    clock.travel(days=15)
    _remove(client, admin_headers, parent)
    client.post(f"/v1/admin/users/{parent['id']}/restore", headers=admin_headers)
    texts = [e["text"] for e in client.get("/v1/admin/dashboard", headers=admin_headers).json()["recent"]]
    assert texts[:4] == ["Restored parent Ada Okafor", "Removed parent Ada Okafor",
                         "Sent a removal notice to parent Ada Okafor", "Cancelled the removal notice for parent Ada Okafor"]
