"""Spec 4 R5: the qualifying exam. Claude is faked (`claude` fixture, helpers.FakeClaude)."""

import pytest
from sqlalchemy import text

from app.domains.exam import service as exam_service
from app.domains.tutors.models import EducationLevel
from tests import helpers


MATHS = exam_service.Tag("mathematics", EducationLevel.senior_secondary, "Mathematics")


@pytest.fixture
def tutor(client):
    """NIN-verified, teaching senior-secondary Mathematics."""
    return helpers.verified_tutor(client)


def start(client, tutor) -> dict:
    response = helpers.start_exam(client, tutor)
    assert response.status_code == 200, response.text
    return response.json()


def answer(client, tutor, attempt, right=20):
    return client.put(f"/v1/exam/attempts/{attempt['id']}/answers", headers=tutor["headers"],
                      json={"answers": helpers.exam_answers(attempt, right)})


def submit(client, tutor, attempt):
    return client.post(f"/v1/exam/attempts/{attempt['id']}/submit", headers=tutor["headers"])


def status(client, tutor) -> dict:
    return client.get("/v1/exam", headers=tutor["headers"]).json()


# ---------- Taking the exam (R5.3-R5.6) ----------

def test_attempt_has_20_questions_and_no_answers_or_explanations(client, db, tutor):
    attempt = start(client, tutor)
    assert len(attempt["questions"]) == 20
    assert [q["position"] for q in attempt["questions"]] == list(range(1, 21))
    for q in attempt["questions"]:
        assert set(q) == {"position", "text", "options", "chosen_index"} and len(q["options"]) == 4
    explanations = [e for (e,) in db.execute(text("SELECT explanation FROM exam_questions"))]
    body = client.get("/v1/exam", headers=tutor["headers"]).text
    assert not any(e in body for e in explanations)
    assert "correct_index" not in body and "explanation" not in body


def test_10_general_and_10_from_the_tutors_subjects(client, db, tutor):
    attempt = start(client, tutor)
    texts = [q["text"] for q in attempt["questions"]]
    assert sum(t.startswith("[General") for t in texts) == 10
    assert sum(t.startswith("[Mathematics senior_secondary]") for t in texts) == 10


def test_subject_questions_are_spread_across_the_tutors_offers(client):
    tutor = helpers.verified_tutor(client, offers=[
        helpers.offer(("Mathematics", "Physics")), helpers.offer(("Biology",), level="junior_secondary")])
    texts = [q["text"] for q in start(client, tutor)["questions"]]
    for tag in ("[Mathematics senior_secondary]", "[Physics senior_secondary]", "[Biology junior_secondary]"):
        assert 3 <= sum(t.startswith(tag) for t in texts) <= 4


def test_answers_are_saved_and_the_open_attempt_resumes(client, tutor):
    attempt = start(client, tutor)
    first = attempt["questions"][0]
    assert answer(client, tutor, {"id": attempt["id"], "questions": [first]}).status_code == 200
    resumed = start(client, tutor)
    assert resumed["id"] == attempt["id"] and resumed["questions"][0]["chosen_index"] is not None
    assert status(client, tutor)["open_attempt"]["id"] == attempt["id"]


@pytest.mark.parametrize("right, passed", [(14, True), (13, False), (20, True), (0, False)])
def test_pass_mark_is_14_of_20(client, tutor, right, passed):
    result = helpers.take_exam(client, tutor, right=right)
    assert (result["score"], result["total"], result["passed"]) == (right, 20, passed)


def test_submit_shows_score_and_pass_fail_but_no_correct_answers(client, tutor):
    attempt = start(client, tutor)
    answer(client, tutor, attempt, right=15)
    response = submit(client, tutor, attempt)
    assert set(response.json()) == {"id", "started_at", "submitted_at", "score", "total", "passed", "seconds_taken"}
    assert helpers.CORRECT not in response.text
    # Submitting again changes nothing, and the attempt's questions aren't shown any more.
    assert submit(client, tutor, attempt).json()["score"] == 15
    assert status(client, tutor)["open_attempt"] is None


def test_unanswered_questions_score_nothing(client, tutor):
    attempt = start(client, tutor)
    assert submit(client, tutor, attempt).json()["score"] == 0


def test_answer_after_30_minutes_is_not_scored(client, clock, tutor):
    attempt = start(client, tutor)
    answer(client, tutor, attempt, right=10)
    clock.travel(minutes=30, seconds=1)
    late = answer(client, tutor, attempt, right=20)
    assert late.status_code == 409 and "Time is up" in late.json()["detail"]
    result = submit(client, tutor, attempt).json()
    assert result["score"] == 10 and not result["passed"] and result["seconds_taken"] == 30 * 60


def test_timed_out_attempt_is_closed_by_the_job(client, db, clock, tutor):
    attempt = start(client, tutor)
    answer(client, tutor, attempt, right=14)
    clock.travel(minutes=31)
    assert helpers.run_jobs(db, clock)["closed_exam_attempts"] == 1
    closed = status(client, tutor)["attempts"][0]
    assert closed["score"] == 14 and closed["passed"] and closed["seconds_taken"] == 30 * 60


def test_exam_needs_a_verified_nin(client):
    tutor = helpers.register_tutor(client)
    response = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert response.status_code == 409 and "Verify your NIN" in response.json()["detail"]


def test_only_tutors_take_it_and_only_their_own_attempts(client, tutor):
    attempt = start(client, tutor)
    other = helpers.verified_tutor(client)
    assert answer(client, other, attempt).status_code == 403
    assert submit(client, other, attempt).status_code == 403
    parent = helpers.register_parent(client)
    assert client.post("/v1/exam/attempts", headers=parent["headers"]).status_code == 403


def test_a_passed_tutor_cannot_take_it_again(client, tutor):
    helpers.take_exam(client, tutor)
    response = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert response.status_code == 409 and "already passed" in response.json()["detail"]


def test_unseen_questions_come_first(client, db, tutor):
    first = {q["text"] for q in start(client, tutor)["questions"]}
    submit(client, tutor, {"id": status(client, tutor)["open_attempt"]["id"]})
    exam_service.add_generated(db, exam_service.GENERAL)
    exam_service.add_generated(db, MATHS)
    second = {q["text"] for q in start(client, tutor)["questions"]}
    assert not first & second


# ---------- Attempts (R5.7) ----------

def test_six_attempts_then_24_hours_then_six_more(client, clock, tutor):
    for left in (5, 4, 3, 2, 1, 0):
        assert not helpers.take_exam(client, tutor, right=0)["passed"]
        assert status(client, tutor)["attempts_left"] == left
        clock.travel(hours=1)
    seventh = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert seventh.status_code == 429 and "try again after" in seventh.json()["detail"]
    assert status(client, tutor)["locked_until"]

    clock.travel(hours=22, minutes=59)  # 23h59m after the 6th started
    assert client.post("/v1/exam/attempts", headers=tutor["headers"]).status_code == 429
    clock.travel(minutes=2)
    assert helpers.take_exam(client, tutor, right=14)["passed"]
    assert len(status(client, tutor)["attempts"]) == 7


def test_the_lock_resets_to_six_more(client, clock, tutor):
    for _ in range(6):
        helpers.take_exam(client, tutor, right=0)
    clock.travel(hours=24, minutes=1)
    assert status(client, tutor)["attempts_left"] == 6
    for _ in range(6):
        helpers.take_exam(client, tutor, right=0)
    assert client.post("/v1/exam/attempts", headers=tutor["headers"]).status_code == 429


# ---------- Question bank (R5.2, R5.8) ----------

def test_empty_bank_says_preparing_and_generates_at_once(client, claude, tutor):
    response = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert response.status_code == 409 and response.json()["detail"] == helpers.PREPARING
    assert {(s, lvl) for s, lvl, _ in claude.generated} == {(None, None), ("Mathematics", "senior_secondary")}
    assert client.post("/v1/exam/attempts", headers=tutor["headers"]).status_code == 200


def test_without_claude_the_tutor_waits(client, monkeypatch, claude, tutor):
    monkeypatch.setattr(exam_service.claude, "available", lambda: False)
    response = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert response.status_code == 409 and response.json()["detail"] == helpers.PREPARING
    assert claude.generated == []


def test_question_the_independent_check_answers_differently_is_discarded(db, claude):
    claude.checker_disagrees = True
    assert exam_service.add_generated(db, exam_service.GENERAL) == 0
    assert db.execute(text("SELECT count(*) FROM exam_questions")).scalar() == 0
    assert len(claude.checked) == 10  # every question was checked

    claude.checker_disagrees = False
    assert exam_service.add_generated(db, exam_service.GENERAL) == 10


def test_checker_sees_only_the_question_and_options(db, claude):
    exam_service.add_generated(db, exam_service.GENERAL, count=1)
    (question, options), = claude.checked
    assert question.startswith("[General") and len(options) == 4
    assert "+" in question and "=" not in question  # the explanation ("n + n = 2n") isn't included


def test_options_are_shuffled_so_the_key_moves(db):
    exam_service.add_generated(db, exam_service.GENERAL, count=10)
    exam_service.add_generated(db, exam_service.GENERAL, count=10)
    keys = {k for (k,) in db.execute(text("SELECT correct_index FROM exam_questions"))}
    assert len(keys) > 1  # all 20 in one position: 4 * (1/4)^20


def test_retired_questions_are_never_served(client, admin_headers, db, tutor):
    exam_service.add_generated(db, exam_service.GENERAL)  # 10 general
    exam_service.add_generated(db, MATHS)
    general = client.get("/v1/admin/exam/questions?general=true", headers=admin_headers).json()
    assert len(general) == 10 and {"correct_index", "explanation"} <= set(general[0])
    retired = client.post(f"/v1/admin/exam/questions/{general[0]['id']}/retire", headers=admin_headers).json()
    assert retired["retired_at"]
    # 9 general left: the bank can't fill an attempt without generating more.
    texts = {q["text"] for q in start(client, tutor)["questions"]}
    assert general[0]["text"] not in texts


def test_top_up_asks_for_every_tag_below_target(db, claude, tutor):
    assert exam_service.top_up_bank(db) == 2
    assert {(s, lvl) for s, lvl, _ in claude.generated} == {(None, None), ("Mathematics", "senior_secondary")}
    bank = {(b.subject, b.level): (b.active, b.target) for b in exam_service.bank_levels(db)}
    assert bank[(None, None)] == (10, 300) and bank[("Mathematics", "senior_secondary")] == (10, 200)


# ---------- Admin (R5.9) and approval (R2.3, R2.4) ----------

def test_admin_sees_every_attempts_score_date_and_time_taken(client, admin_headers, clock, tutor):
    attempt = start(client, tutor)
    answer(client, tutor, attempt, right=16)
    clock.travel(minutes=12)
    submit(client, tutor, attempt)
    seen = client.get(f"/v1/admin/exam/attempts?tutor_id={tutor['id']}", headers=admin_headers).json()
    assert len(seen) == 1
    assert (seen[0]["score"], seen[0]["passed"], seen[0]["seconds_taken"]) == (16, True, 12 * 60)
    assert seen[0]["started_at"] and seen[0]["tutor_name"]
    for path in ("/v1/admin/exam/attempts", "/v1/admin/exam/questions", "/v1/admin/exam/bank"):
        assert client.get(path, headers=tutor["headers"]).status_code == 403


def test_no_tutor_is_approved_without_passing(client, admin_headers):
    tutor = helpers.certified_tutor(client, admin_headers)
    response = helpers.vet(client, admin_headers, tutor)
    assert response.status_code == 409 and "qualifying exam not passed" in response.json()["detail"]
    helpers.take_exam(client, tutor, right=13)
    assert helpers.vet(client, admin_headers, tutor).status_code == 409
    helpers.take_exam(client, tutor, right=14)
    steps = {s["key"]: s for s in client.get("/v1/onboarding", headers=tutor["headers"]).json()["steps"]}
    assert steps["quiz"]["done"]
    assert helpers.vet(client, admin_headers, tutor).status_code == 200
