"""Claude (Anthropic) for the qualifying exam's question bank (spec 4 R5.2). Called only from here.

Two kinds of request, both returning JSON through structured outputs:
- `generate_questions`: a batch of multiple-choice questions for one tag (general reasoning, or a
  subject at a level), each with four options, the correct letter and a short explanation.
- `answer_question`: an independent solve of one question, shown without the key or explanation.
  The bank keeps a question only when this answer matches the generator's key.

Refusals are rerouted server-side (`fallbacks: "default"`); a request that still refuses, runs out of
tokens or fails returns nothing here and the caller simply has fewer questions.
"""

import json
import logging
from dataclasses import dataclass

import anthropic

from app.core.config import is_placeholder, settings

logger = logging.getLogger(__name__)

LETTERS = ("A", "B", "C", "D")
FALLBACK_BETA = "server-side-fallback-2026-07-01"

LEVEL_NAMES = {"primary": "primary school (Primary 1-6)",
               "junior_secondary": "junior secondary school (JSS 1-3)",
               "senior_secondary": "senior secondary school (SSS 1-3, WAEC/NECO level)"}

GENERATOR_SYSTEM = """You write questions for TutorLink's qualifying exam. TutorLink is a Nigerian marketplace \
for home tutors; every tutor must pass this exam before parents can book them. The exam is meant to \
separate tutors who can genuinely think and teach from those who cannot.

Write questions that need several steps of reasoning or problem solving to answer: combining facts, \
working through a calculation, interpreting a short passage or data set, spotting the flaw in an \
argument, or applying a concept to an unfamiliar situation. Avoid questions that can be answered by \
recall alone, trick questions, and questions whose answer depends on opinion or on facts that change \
over time.

Each question has exactly four options (A-D) and exactly one correct answer. The three wrong options \
should be plausible mistakes a weaker candidate would make. Put everything the candidate needs in the \
question itself; it is shown as plain text, so write maths in plain text (e.g. 3x^2 + 2x - 5 = 0). \
Vary the position of the correct answer. The explanation (one to three sentences) says why the \
correct option is right; it is never shown to candidates."""

CHECKER_SYSTEM = """You are taking a multiple-choice exam. Work the question out carefully, then give \
the letter of the single best option."""

GENERATED_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "option_a": {"type": "string"},
                    "option_b": {"type": "string"},
                    "option_c": {"type": "string"},
                    "option_d": {"type": "string"},
                    "correct": {"type": "string", "enum": list(LETTERS)},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "option_a", "option_b", "option_c", "option_d", "correct", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["questions"],
    "additionalProperties": False,
}

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string", "enum": list(LETTERS)}},
    "required": ["answer"],
    "additionalProperties": False,
}


@dataclass
class GeneratedQuestion:
    text: str
    options: list[str]  # four, in A-D order
    correct_index: int  # 0-3
    explanation: str


def available() -> bool:
    return not is_placeholder(settings.ANTHROPIC_API_KEY)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=3)


def _json_reply(system: str, prompt: str, schema: dict) -> dict | None:
    """One request with a JSON-schema answer, or None if Claude declined, ran out of tokens or failed."""
    try:
        response = _client().beta.messages.create(
            model=settings.EXAM_MODEL,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APIError:
        logger.exception("Claude request for the exam bank failed")
        return None
    if response.stop_reason != "end_turn":
        logger.warning("Claude stopped with %s (request %s)", response.stop_reason, response._request_id)
        return None
    text = next((b.text for b in response.content if b.type == "text"), None)
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        logger.warning("Claude returned invalid JSON (request %s)", response._request_id)
        return None


def generate_questions(subject: str | None, level: str | None, count: int,
                       avoid: list[str]) -> list[GeneratedQuestion]:
    """`count` new questions: general reasoning when `subject` is None, otherwise `subject` at `level`.
    `avoid` lists existing questions on the same tag, so new ones differ from them."""
    if subject is None:
        topic = ("general reasoning: logical deduction, quantitative reasoning, reading comprehension "
                 "and interpreting simple data. Any educated adult should be able to answer them with "
                 "careful thought; no specialist subject knowledge")
    else:
        topic = (f"{subject} as taught at {LEVEL_NAMES.get(level or '', level)} in Nigeria. The tutor will "
                 f"teach this, so test whether they can solve the hardest problems a strong student at "
                 f"this level meets, using the Nigerian curriculum")
    prompt = f"Write {count} questions on {topic}."
    if avoid:
        listed = "\n".join(f"- {q[:200]}" for q in avoid)
        prompt += f"\n\nThe bank already has these; write different ones:\n{listed}"
    data = _json_reply(GENERATOR_SYSTEM, prompt, GENERATED_SCHEMA)
    if not data:
        return []
    return [GeneratedQuestion(text=q["question"].strip(),
                              options=[q[f"option_{x}"].strip() for x in "abcd"],
                              correct_index=LETTERS.index(q["correct"]),
                              explanation=q["explanation"].strip())
            for q in data.get("questions", [])]


def answer_question(text: str, options: list[str]) -> int | None:
    """An independent answer (0-3) to a question, given without its key, or None if there's no answer."""
    listed = "\n".join(f"{letter}. {option}" for letter, option in zip(LETTERS, options))
    data = _json_reply(CHECKER_SYSTEM, f"{text}\n\n{listed}", ANSWER_SCHEMA)
    return LETTERS.index(data["answer"]) if data else None
