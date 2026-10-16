"""Spec 12: admins write the exam questions, and no tutor sees a question twice."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import anthropic
import httpx
import pytest
from sqlmodel import select

from app.core import claude as claude_client
from app.core.config import settings
from app.domains.exam import service as exam_service
from app.domains.exam.models import ExamAttemptQuestion, ExamQuestion
from tests import helpers


def text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF with real text, one line per entry."""
    ops = ["BT", "/F1 11 Tf", "14 TL", "50 800 Td"]
    for line in lines:
        ops.append("(" + line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") Tj T*")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
               b"/Resources << /Font << /F1 5 0 R >> >> >>",
               b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def question(text: str = "What is the capital of Nigeria?", subject: str | None = None,
             level: str | None = None, correct: int = 1, options=("Lagos", "Abuja", "Kano", "Ibadan")) -> dict:
    return {"text": text, "options": list(options), "correct_index": correct, "subject": subject, "level": level,
            "explanation": "Abuja became the capital in 1991."}


def add(client, admin_headers, **kwargs):
    return client.post("/v1/admin/exam/questions", headers=admin_headers, json=question(**kwargs))


def fill_bank(client, admin_headers, general: int, maths: int, prefix: str = "") -> None:
    """Admin questions only: `general` general reasoning and `maths` senior-secondary Mathematics."""
    for tag, count in ((None, general), ("Mathematics", maths)):
        body = {"subject": tag, "level": "senior_secondary" if tag else None, "questions": [
            {"text": f"{prefix}{tag or 'General'} question number {i}?", "options": ["w", "x", "y", "z"],
             "correct_index": i % 4} for i in range(count)]}
        if count:
            response = client.post("/v1/admin/exam/questions/batch", headers=admin_headers, json=body)
            assert response.status_code == 201, response.text


def read_pdf(client, admin_headers, data: bytes):
    return client.post("/v1/admin/exam/questions/pdf", headers=admin_headers,
                       files={"file": ("questions.pdf", data, "application/pdf")})


@pytest.fixture
def no_claude(monkeypatch):
    """Claude isn't available: only admins' questions are in the bank."""
    monkeypatch.setattr(claude_client, "available", lambda: False)


def ready_tutor_without_exam(client, admin_headers) -> dict:
    return helpers.certified_tutor(client, admin_headers)


# ---------- R1: writing a question ----------

def test_admins_write_general_and_subject_questions(client, admin_headers):
    general = add(client, admin_headers)
    assert general.status_code == 201, general.text
    assert general.json()["subject"] is None and general.json()["model"] == "admin"
    assert general.json()["added_by_name"]  # the admin's name or email (R3.1)
    maths = add(client, admin_headers, text="What is 12 divided by 4?", subject="mathematics", level="primary",
                options=("2", "3", "4", "6"))
    assert maths.status_code == 201 and maths.json()["subject"] == "Mathematics"

    assert add(client, admin_headers, text="What is the capital  OF nigeria?").status_code == 409  # duplicate (R1.3)
    for bad in ({"options": ("a", "b", "c")}, {"options": ("a", "a", "b", "c")},
                {"subject": "Astrology", "level": "primary"}, {"subject": None, "level": "primary"},
                {"text": "Too short"}):
        assert add(client, admin_headers, text=bad.pop("text", "A perfectly fine question?"), **bad).status_code == 422, bad
    parent = helpers.register_parent(client)
    assert add(client, parent["headers"]).status_code == 403


# ---------- R2: PDF upload ----------

LAYOUT = ["Mathematics, senior secondary", "1. What is 3 x 4? Think", "carefully.", "A. 7", "B) 12", "C. 34",
          "D. 1", "Answer: B", "Explanation: 3 groups of 4 make 12.", "2) Which of these is a prime number?",
          "A. 4", "B. 6", "C. 7", "Answer: c", "3. Which number is even?", "A. 3", "B. 5", "C. 8", "D. 9"]


def test_a_pdf_is_read_for_checking_and_nothing_is_saved(client, db, admin_headers):
    response = read_pdf(client, admin_headers, text_pdf(LAYOUT))
    assert response.status_code == 200, response.text
    found = response.json()
    assert [q["number"] for q in found["questions"]] == [1, 2, 3]
    first = found["questions"][0]
    assert first == {"number": 1, "text": "What is 3 x 4? Think carefully.", "options": ["7", "12", "34", "1"],
                     "correct_index": 1, "explanation": "3 groups of 4 make 12."}
    assert {(p["number"], p["message"]) for p in found["problems"]} == {
        (2, "No option D"), (3, "No \"Answer:\" line with a letter A to D")}
    assert db.exec(select(ExamQuestion)).all() == []


def test_checked_questions_are_saved_and_duplicates_skipped(client, admin_headers):
    found = read_pdf(client, admin_headers, text_pdf(LAYOUT)).json()["questions"]
    first = {k: found[0][k] for k in ("text", "options", "correct_index", "explanation")}
    body = {"subject": "Mathematics", "level": "senior_secondary",
            "questions": [first, {**first, "text": "WHAT is 3 x 4?  think carefully."},
                          {"text": "Which of these is a prime number?", "options": ["4", "6", "7", "9"], "correct_index": 2}]}
    saved = client.post("/v1/admin/exam/questions/batch", headers=admin_headers, json=body)
    assert saved.status_code == 201 and saved.json() == {"added": 2, "duplicates": 1}
    again = client.post("/v1/admin/exam/questions/batch", headers=admin_headers, json=body)
    assert again.json() == {"added": 0, "duplicates": 3}
    texts = [e["text"] for e in client.get("/v1/admin/dashboard", headers=admin_headers).json()["recent"]]
    assert "Added 2 exam questions for Mathematics (senior secondary) from a PDF" in texts  # R3.3


def test_a_pdf_without_the_layout_or_not_a_pdf_is_refused(client, admin_headers):
    no_questions = read_pdf(client, admin_headers, text_pdf(["Just some notes about the exam."]))
    assert no_questions.status_code == 422 and "Answer: B" in no_questions.json()["detail"]
    assert read_pdf(client, admin_headers, b"not a pdf").status_code == 422
    assert read_pdf(client, admin_headers, b"%PDF-1.4 broken").status_code == 422


# ---------- R3: the bank ----------

def test_admin_questions_are_served_and_claude_tops_up_only_when_short(client, db, admin_headers, claude):
    fill_bank(client, admin_headers, general=exam_service.GENERAL_TARGET, maths=exam_service.SUBJECT_TARGET)
    tutor = ready_tutor_without_exam(client, admin_headers)
    attempt = helpers.start_exam(client, tutor)
    assert attempt.status_code == 200, attempt.text
    served = {q.model for q in db.exec(select(ExamQuestion).join(
        ExamAttemptQuestion, ExamAttemptQuestion.question_id == ExamQuestion.id)).all()}
    assert served == {"admin"}
    with patch.object(exam_service, "request_generation") as asked:
        exam_service.top_up_bank(db)
    assert asked.call_args.args[0] == []  # every tag is at its target: Claude isn't asked


def test_a_rejected_api_key_pauses_claude_for_an_hour(monkeypatch):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-" + "k" * 40)
    monkeypatch.setattr(claude_client, "_paused_until", None)
    error = anthropic.AuthenticationError("invalid x-api-key", response=httpx.Response(
        401, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")), body=None)

    class Rejecting:
        class beta:
            class messages:
                @staticmethod
                def create(**kwargs):
                    raise error

    monkeypatch.setattr(claude_client, "_client", lambda: Rejecting)
    assert claude_client._json_reply("system", "prompt", {"type": "object"}) is None
    paused = claude_client._paused_until  # the `claude` fixture fakes available(), so check the pause it reads
    now = datetime.now(timezone.utc)
    assert paused is not None and timedelta(minutes=59) < paused - now <= timedelta(hours=1)  # R3.2


# ---------- R4: no repeats ----------

def test_a_tutor_never_gets_a_question_twice(client, db, admin_headers, no_claude):
    fill_bank(client, admin_headers, general=20, maths=20)  # exactly two attempts' worth
    tutor = ready_tutor_without_exam(client, admin_headers)
    seen: set[str] = set()
    for _ in range(2):
        attempt = client.post("/v1/exam/attempts", headers=tutor["headers"]).json()
        texts = {q["text"] for q in attempt["questions"]}
        assert len(texts) == 20 and not texts & seen
        seen |= texts
        assert client.post(f"/v1/exam/attempts/{attempt['id']}/submit", headers=tutor["headers"]).status_code == 200

    refused = client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert refused.status_code == 409 and refused.json()["detail"] == exam_service.PREPARING
    other = ready_tutor_without_exam(client, admin_headers)  # a different tutor can have the same questions
    assert client.post("/v1/exam/attempts", headers=other["headers"]).status_code == 200


def test_admins_are_told_once_a_day_which_subject_needs_questions(client, admin_headers, no_claude, clock):
    fill_bank(client, admin_headers, general=10, maths=0)
    tutor = ready_tutor_without_exam(client, admin_headers)
    for _ in range(2):
        assert client.post("/v1/exam/attempts", headers=tutor["headers"]).status_code == 409

    def needed():
        return [n["title"] for n in client.get("/v1/notifications/me", headers=admin_headers).json()["items"]
                if n["title"].startswith("Exam questions needed")]
    assert needed() == ["Exam questions needed: Mathematics (senior secondary)"]
    clock.travel(days=1, minutes=1)
    client.post("/v1/exam/attempts", headers=tutor["headers"])
    assert len(needed()) == 2


# ---------- R5: the help assistant ----------

def test_the_help_assistant_uses_haiku_without_fallbacks(monkeypatch):
    calls = []

    class Recording:
        class beta:
            class messages:
                @staticmethod
                async def create(**kwargs):
                    calls.append(kwargs)
                    raise anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))

    import asyncio
    monkeypatch.setattr(claude_client, "_async_client", lambda: Recording)
    asyncio.run(claude_client.help_reply("parent", [{"role": "user", "content": "Hi"}]))
    assert settings.HELP_MODEL == "claude-haiku-5-5"
    assert calls[0]["model"] == "claude-haiku-5-5" and "fallbacks" not in calls[0] and "betas" not in calls[0]
