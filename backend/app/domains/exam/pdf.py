"""Reads exam questions from a PDF in TutorLink's fixed layout (spec 12 R2). Nothing is saved here: the admin checks
what was found first.

    1. What is 3 x 4?
    A. 7
    B. 12
    C. 34
    D. 1
    Answer: B
    Explanation: 3 groups of 4 make 12.      (optional)
"""

import io
import logging
import re

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader

from app.domains.exam.models import ParsedQuestions, ParseProblem, QuestionDraft

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024
LAYOUT = ("Each question needs a number (\"1.\"), four options (\"A.\" to \"D.\") and an answer line (\"Answer: B\"). "
          "Use a PDF with real text, not a scan or a photo.")

QUESTION = re.compile(r"^\s*(\d{1,4})\s*[.)]\s+(.*)$")
OPTION = re.compile(r"^\s*([A-Da-d])\s*[.)]\s+(.*)$")
ANSWER = re.compile(r"^\s*answer\s*[:\-]\s*\(?([A-Da-d])\)?\s*\.?\s*$", re.IGNORECASE)
EXPLANATION = re.compile(r"^\s*explanation\s*[:\-]\s*(.*)$", re.IGNORECASE)


def _text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        logger.info("An uploaded exam PDF couldn't be read", exc_info=True)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"This PDF couldn't be read. {LAYOUT}")


def read_upload(file: UploadFile) -> bytes:
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The PDF can be at most 10 MB")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload a PDF file")
    return data


def parse(data: bytes) -> ParsedQuestions:
    """Every numbered question found, with what's wrong with each (R2.3). A 422 if none are found (R2.5)."""
    blocks: list[dict] = []
    part: str | None = None  # what a line that doesn't start a new part continues
    for raw in _text(data).splitlines():
        line = raw.strip()
        if not line:
            continue
        if m := QUESTION.match(line):
            blocks.append({"number": int(m[1]), "text": m[2], "options": {}, "answer": None, "explanation": None,
                           "repeats": []})
            part = "text"
            continue
        if not blocks:
            continue  # a heading or notes before the first question
        block = blocks[-1]
        if m := ANSWER.match(line):
            block["answer"] = m[1].upper()
            part = None
        elif m := EXPLANATION.match(line):
            block["explanation"] = m[1]
            part = "explanation"
        elif m := OPTION.match(line):
            letter = m[1].upper()
            if letter in block["options"]:
                block["repeats"].append(letter)
            block["options"][letter] = m[2]
            part = letter
        elif part == "text":
            block["text"] += " " + line
        elif part == "explanation":
            block["explanation"] += " " + line
        elif part in block["options"]:
            block["options"][part] += " " + line

    if not blocks:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"No questions were found in this PDF. {LAYOUT}")

    questions, problems = [], []
    for b in blocks:
        missing = [letter for letter in "ABCD" if letter not in b["options"]]
        if missing:
            problems.append(ParseProblem(number=b["number"], message=f"No option {', '.join(missing)}"))
        if b["repeats"]:
            problems.append(ParseProblem(number=b["number"], message=f"Option {', '.join(b['repeats'])} appears twice"))
        if b["answer"] is None:
            problems.append(ParseProblem(number=b["number"], message="No \"Answer:\" line with a letter A to D"))
        if len(b["text"].strip()) < 10:
            problems.append(ParseProblem(number=b["number"], message="The question text is too short"))
        questions.append(QuestionDraft(
            number=b["number"], text=" ".join(b["text"].split()),
            options=[" ".join(b["options"].get(letter, "").split()) for letter in "ABCD"],
            correct_index="ABCD".index(b["answer"]) if b["answer"] else None,
            explanation=" ".join(b["explanation"].split()) if b["explanation"] else None,
        ))
    return ParsedQuestions(questions=questions, problems=problems)
