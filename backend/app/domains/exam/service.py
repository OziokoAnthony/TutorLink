"""The qualifying exam (spec 4 R5).

Bank: Claude writes questions per tag (general reasoning, or a subject at a level); a second, independent
Claude call answers each one without the key, and only questions it gets right are kept (R5.2). The bank
is topped up in the background towards 300 general and 200 per subject and level in use (R5.2), and
on demand when an attempt can't be filled yet (R5.8).

Attempts: 20 questions (10 general, 10 from the tutor's offers), 30 minutes on the server clock, pass
at 14. Up to 6 attempts, then a 24-hour lock from the 6th, then 6 more (R5.3-R5.7).
"""

import hashlib
import logging
import random
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core import claude, clock
from app.core.config import settings
from app.db.session import engine
from app.domains.auth.models import User
from app.domains.exam.models import (
    GENERAL_KEY,
    AdminAttempt,
    AdminQuestion,
    AnswersIn,
    AttemptQuestionView,
    AttemptResult,
    AttemptView,
    BankLevel,
    ExamAttempt,
    ExamAttemptQuestion,
    ExamQuestion,
    ExamStatus,
)
from app.domains.tutors import subjects as subject_list
from app.domains.tutors.models import (
    EducationLevel,
    TutorOffer,
    TutorOfferSubject,
    TutorProfile,
)

logger = logging.getLogger(__name__)

GENERAL_COUNT = 10  # per attempt (R5.3)
SUBJECT_COUNT = 10
MINUTES = 30  # R5.4
PASS_MARK = 14  # of 20: 70% (R5.6)
ATTEMPTS_PER_ROUND = 6  # R5.7
LOCK = timedelta(hours=24)
GENERAL_TARGET = 300  # R5.2
SUBJECT_TARGET = 200
BATCH = 10  # questions asked of Claude per request
AVOID = 40  # recent questions shown to Claude so new ones differ

PREPARING = "Your exam is being prepared, try again shortly"


@dataclass(frozen=True)
class Tag:
    subject_key: str  # GENERAL_KEY for general reasoning
    level: EducationLevel | None
    subject: str | None = None  # display name; not part of equality

    def __eq__(self, other):
        return isinstance(other, Tag) and (self.subject_key, self.level) == (other.subject_key, other.level)

    def __hash__(self):
        return hash((self.subject_key, self.level))

    @property
    def target(self) -> int:
        return GENERAL_TARGET if self.subject_key == GENERAL_KEY else SUBJECT_TARGET


GENERAL = Tag(GENERAL_KEY, None)


def _tag_filter(tag: Tag):
    level = ExamQuestion.level.is_(None) if tag.level is None else ExamQuestion.level == tag.level
    return (ExamQuestion.subject_key == tag.subject_key) & level


def _active_filter():
    return ExamQuestion.retired_at.is_(None)


def _tags_from(rows) -> list[Tag]:
    """Only listed subjects: an offer saved before the list was enforced may hold free text, which must never
    reach Claude's prompt."""
    tags: dict[Tag, Tag] = {}
    for subject, level in rows:
        name = subject_list.canonical(subject)
        if name is None:
            continue
        tag = Tag(name.lower(), level, name)
        tags.setdefault(tag, tag)
    return sorted(tags.values(), key=lambda t: (t.subject_key, t.level.value))


def tutor_tags(session: Session, tutor_id: UUID) -> list[Tag]:
    """The subjects and levels of the tutor's active offers."""
    return _tags_from(session.exec(
        select(TutorOfferSubject.subject, TutorOffer.level)
        .join(TutorOffer, TutorOffer.id == TutorOfferSubject.offer_id)
        .where(TutorOffer.tutor_id == tutor_id, TutorOffer.is_active == True)  # noqa: E712
    ).all())


def tags_in_use(session: Session) -> list[Tag]:
    """Every subject and level in some tutor's active offer: the bank keeps these filled (R5.2)."""
    return _tags_from(session.exec(
        select(TutorOfferSubject.subject, TutorOffer.level)
        .join(TutorOffer, TutorOffer.id == TutorOfferSubject.offer_id)
        .where(TutorOffer.is_active == True)  # noqa: E712
        .distinct()
    ).all())


# ---------- Question bank (R5.2) ----------

def _normal(text: str) -> str:
    return " ".join(text.lower().split())


def _hash(text: str) -> str:
    return hashlib.sha256(_normal(text).encode()).hexdigest()


def active_count(session: Session, tag: Tag) -> int:
    return session.exec(select(func.count()).select_from(ExamQuestion)
                        .where(_tag_filter(tag), _active_filter())).one()


def _well_formed(q: claude.GeneratedQuestion) -> bool:
    options = [_normal(o) for o in q.options]
    return (len(q.text) >= 20 and len(options) == 4 and all(options) and len(set(options)) == 4
            and 0 <= q.correct_index <= 3)


def add_generated(session: Session, tag: Tag, count: int = BATCH) -> int:
    """Asks Claude for `count` questions on `tag`, keeps those an independent answer confirms, and
    returns how many were added. Options are shuffled so the key isn't always in Claude's position."""
    avoid = list(session.exec(select(ExamQuestion.text).where(_tag_filter(tag))
                              .order_by(ExamQuestion.created_at.desc()).limit(AVOID)).all())
    level = tag.level.value if tag.level else None
    generated = [q for q in claude.generate_questions(tag.subject, level, count, avoid) if _well_formed(q)]
    # The second, independent call sees the question and options only (R5.2).
    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = list(pool.map(lambda q: claude.answer_question(q.text, q.options), generated))

    added = 0
    for question, answer in zip(generated, answers):
        if answer != question.correct_index:
            logger.info("Discarded a generated %s question: the independent answer differed",
                        tag.subject or "general")
            continue
        order = random.sample(range(4), 4)
        row = ExamQuestion(
            subject_key=tag.subject_key, subject=tag.subject, level=tag.level, text=question.text,
            options=[question.options[i] for i in order], correct_index=order.index(question.correct_index),
            explanation=question.explanation, text_hash=_hash(question.text), model=settings.EXAM_MODEL,
        )
        try:
            with session.begin_nested():
                session.add(row)
            added += 1
        except IntegrityError:  # already in the bank
            pass
    session.commit()
    return added


# Generation runs off the request thread: Claude takes a while and the tutor is told to come back.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="exam-bank")
_in_flight: set[Tag] = set()
_in_flight_lock = threading.Lock()


def new_session() -> Session:
    return Session(engine)


def run_in_background(fn, *args) -> None:
    _executor.submit(fn, *args)


def _generate_in_background(tag: Tag) -> None:
    try:
        with new_session() as session:
            added = add_generated(session, tag)
        logger.info("Exam bank: added %d %s questions", added, tag.subject or "general")
    except Exception:
        logger.exception("Exam bank generation failed")
    finally:
        with _in_flight_lock:
            _in_flight.discard(tag)


def request_generation(tags: list[Tag]) -> int:
    """Starts one batch for each tag not already being generated. Returns how many were started."""
    if not claude.available():
        logger.warning("ANTHROPIC_API_KEY isn't set: the exam bank can't be topped up")
        return 0
    started = 0
    for tag in tags:
        with _in_flight_lock:
            if tag in _in_flight:
                continue
            _in_flight.add(tag)
        run_in_background(_generate_in_background, tag)
        started += 1
    return started


def top_up_bank(session: Session) -> int:
    """A scheduled pass (app/jobs.py): one more batch for every tag below its target."""
    short = [t for t in (GENERAL, *tags_in_use(session)) if active_count(session, t) < t.target]
    return request_generation(short)


# ---------- Attempts ----------

def _close(session: Session, attempt: ExamAttempt, now: datetime) -> None:
    """Scores an attempt from the answers saved before its deadline (R5.4)."""
    if attempt.submitted_at is not None:
        return
    rows = session.exec(
        select(ExamAttemptQuestion.chosen_index, ExamQuestion.correct_index)
        .join(ExamQuestion, ExamQuestion.id == ExamAttemptQuestion.question_id)
        .where(ExamAttemptQuestion.attempt_id == attempt.id)
    ).all()
    attempt.score = sum(1 for chosen, correct in rows if chosen == correct)
    attempt.passed = attempt.score >= PASS_MARK
    attempt.submitted_at = min(now, attempt.deadline)
    session.add(attempt)


def close_expired(session: Session, now: datetime, tutor_id: UUID | None = None) -> int:
    """Scores attempts whose time ran out without being submitted. Catch-up pass for app/jobs.py."""
    stmt = select(ExamAttempt).where(ExamAttempt.submitted_at.is_(None), ExamAttempt.deadline < now)
    if tutor_id:
        stmt = stmt.where(ExamAttempt.tutor_id == tutor_id)
    attempts = list(session.exec(stmt.with_for_update(skip_locked=True)).all())
    for attempt in attempts:
        _close(session, attempt, now)
    session.commit()
    return len(attempts)


def _attempts(session: Session, tutor_id: UUID) -> list[ExamAttempt]:
    return list(session.exec(select(ExamAttempt).where(ExamAttempt.tutor_id == tutor_id)
                             .order_by(ExamAttempt.started_at)).all())


def _current_round(attempts: list[ExamAttempt]) -> list[ExamAttempt]:
    """The attempts since the last reset: a 7th attempt can only start after the lock, and starts a
    new round of 6 (R5.7)."""
    current: list[ExamAttempt] = []
    for attempt in attempts:
        if len(current) == ATTEMPTS_PER_ROUND:
            current = []
        current.append(attempt)
    return current


def _limits(attempts: list[ExamAttempt], now: datetime) -> tuple[int, datetime | None]:
    """(attempts left, locked until)."""
    current = _current_round(attempts)
    if len(current) < ATTEMPTS_PER_ROUND:
        return ATTEMPTS_PER_ROUND - len(current), None
    unlocks = current[-1].started_at + LOCK
    return (0, unlocks) if now < unlocks else (ATTEMPTS_PER_ROUND, None)


def has_passed(session: Session, tutor_id: UUID) -> bool:
    return session.exec(select(ExamAttempt.id).where(
        ExamAttempt.tutor_id == tutor_id, ExamAttempt.passed == True)).first() is not None  # noqa: E712


def _result(attempt: ExamAttempt) -> AttemptResult:
    return AttemptResult(id=attempt.id, started_at=attempt.started_at, submitted_at=attempt.submitted_at,
                         score=attempt.score, total=attempt.total, passed=attempt.passed,
                         seconds_taken=int((attempt.submitted_at - attempt.started_at).total_seconds()))


def _view(session: Session, attempt: ExamAttempt) -> AttemptView:
    rows = session.exec(
        select(ExamAttemptQuestion, ExamQuestion)
        .join(ExamQuestion, ExamQuestion.id == ExamAttemptQuestion.question_id)
        .where(ExamAttemptQuestion.attempt_id == attempt.id)
        .order_by(ExamAttemptQuestion.position)
    ).all()
    return AttemptView(id=attempt.id, started_at=attempt.started_at, deadline=attempt.deadline, questions=[
        AttemptQuestionView(position=aq.position, text=q.text, options=q.options, chosen_index=aq.chosen_index)
        for aq, q in rows])


def get_status(session: Session, user: User) -> ExamStatus:
    now = clock.now()
    close_expired(session, now, user.id)
    attempts = _attempts(session, user.id)
    left, locked_until = _limits(attempts, now)
    open_attempt = next((a for a in attempts if a.submitted_at is None), None)
    return ExamStatus(
        passed=any(a.passed for a in attempts), open_attempt=_view(session, open_attempt) if open_attempt else None,
        attempts_left=left, locked_until=locked_until,
        attempts=[_result(a) for a in reversed(attempts) if a.submitted_at is not None],
        pass_mark=PASS_MARK, total=GENERAL_COUNT + SUBJECT_COUNT, minutes=MINUTES,
    )


def _pool(session: Session, tag: Tag, seen: set[UUID]) -> list[ExamQuestion]:
    """Active questions on `tag`, unseen ones first, random within each group (R5.3)."""
    questions = list(session.exec(select(ExamQuestion).where(_tag_filter(tag), _active_filter())).all())
    random.shuffle(questions)
    return sorted(questions, key=lambda q: q.id in seen)


def _pick(session: Session, tutor_id: UUID, tags: list[Tag]) -> list[ExamQuestion]:
    """10 general and 10 subject questions spread across the tutor's subjects and levels (R5.3).
    Asks for more questions where the bank is short, and refuses if it can't fill an attempt (R5.8)."""
    seen = set(session.exec(
        select(ExamAttemptQuestion.question_id)
        .join(ExamAttempt, ExamAttempt.id == ExamAttemptQuestion.attempt_id)
        .where(ExamAttempt.tutor_id == tutor_id)
    ).all())
    general = _pool(session, GENERAL, seen)
    pools = {tag: _pool(session, tag, seen) for tag in tags}

    short = ([GENERAL] if len(general) < GENERAL_COUNT else []) + [t for t, p in pools.items() if len(p) < SUBJECT_COUNT]
    if short:
        request_generation(short)
    if len(general) < GENERAL_COUNT or sum(len(p) for p in pools.values()) < SUBJECT_COUNT:
        raise HTTPException(status.HTTP_409_CONFLICT, PREPARING)

    subject: list[ExamQuestion] = []
    queues = [list(p) for p in pools.values()]
    random.shuffle(queues)
    while len(subject) < SUBJECT_COUNT:  # round robin across subjects and levels
        for queue in queues:
            if queue and len(subject) < SUBJECT_COUNT:
                subject.append(queue.pop(0))
    chosen = general[:GENERAL_COUNT] + subject
    random.shuffle(chosen)
    return chosen


def start_attempt(session: Session, user: User) -> AttemptView:
    """Starts an attempt, or returns the one in progress."""
    now = clock.now()
    close_expired(session, now, user.id)
    # Locked so two clicks can't start two attempts.
    profile = session.exec(select(TutorProfile).where(TutorProfile.user_id == user.id).with_for_update()).first()
    if profile is None or profile.nin_verified_at is None:
        # The exam comes after identity is confirmed (spec 4 R3.4).
        raise HTTPException(status.HTTP_409_CONFLICT, "Verify your NIN before taking the exam")
    attempts = _attempts(session, user.id)
    if any(a.passed for a in attempts):
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already passed the qualifying exam")
    if (open_attempt := next((a for a in attempts if a.submitted_at is None), None)) is not None:
        return _view(session, open_attempt)
    left, locked_until = _limits(attempts, now)
    if locked_until is not None:
        at = locked_until.astimezone(clock.WAT).strftime("%H:%M on %d %b")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"You've used all {ATTEMPTS_PER_ROUND} attempts. You can try again after {at} (WAT).")
    tags = tutor_tags(session, user.id)
    if not tags:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Add an offer with subjects from TutorLink's list first: the exam covers the subjects you teach")

    questions = _pick(session, user.id, tags)
    attempt = ExamAttempt(tutor_id=user.id, started_at=now, deadline=now + timedelta(minutes=MINUTES),
                          total=len(questions))
    session.add(attempt)
    session.flush()
    for position, question in enumerate(questions, start=1):
        session.add(ExamAttemptQuestion(attempt_id=attempt.id, question_id=question.id, position=position))
    session.commit()
    session.refresh(attempt)
    return _view(session, attempt)


def _own_attempt(session: Session, user: User, attempt_id: UUID) -> ExamAttempt:
    attempt = session.exec(select(ExamAttempt).where(ExamAttempt.id == attempt_id).with_for_update()).first()
    if attempt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attempt not found")
    if attempt.tutor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This isn't your attempt")
    return attempt


def save_answers(session: Session, user: User, attempt_id: UUID, data: AnswersIn) -> AttemptView:
    """Saves answers as the tutor goes. After the deadline nothing more is saved (R5.4)."""
    attempt = _own_attempt(session, user, attempt_id)
    if attempt.submitted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This attempt is finished")
    now = clock.now()
    if now > attempt.deadline:
        _close(session, attempt, now)
        session.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Time is up: answers after 30 minutes aren't counted")
    rows = {r.position: r for r in session.exec(
        select(ExamAttemptQuestion).where(ExamAttemptQuestion.attempt_id == attempt.id)).all()}
    for answer in data.answers:
        if answer.position not in rows:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"There's no question {answer.position}")
        rows[answer.position].chosen_index = answer.choice
        session.add(rows[answer.position])
    session.commit()
    return _view(session, attempt)


def submit(session: Session, user: User, attempt_id: UUID) -> AttemptResult:
    """Scores the attempt. The tutor sees the score and pass/fail only, never the answers (R5.5)."""
    attempt = _own_attempt(session, user, attempt_id)
    _close(session, attempt, clock.now())
    session.commit()
    session.refresh(attempt)
    return _result(attempt)


# ---------- Admin (R5.2, R5.9) ----------

def admin_attempts(session: Session, tutor_id: UUID | None) -> list[AdminAttempt]:
    stmt = (select(ExamAttempt, TutorProfile.full_name)
            .join(TutorProfile, TutorProfile.user_id == ExamAttempt.tutor_id)
            .where(ExamAttempt.submitted_at.is_not(None)))
    if tutor_id:
        stmt = stmt.where(ExamAttempt.tutor_id == tutor_id)
    rows = session.exec(stmt.order_by(ExamAttempt.started_at.desc()).limit(500)).all()
    return [AdminAttempt(**_result(a).model_dump(), tutor_id=a.tutor_id, tutor_name=name) for a, name in rows]


def admin_questions(session: Session, subject: str | None, level: EducationLevel | None, general: bool,
                    include_retired: bool, skip: int, limit: int) -> list[AdminQuestion]:
    stmt = select(ExamQuestion)
    if general:
        stmt = stmt.where(_tag_filter(GENERAL))
    else:
        if subject:
            stmt = stmt.where(ExamQuestion.subject_key == subject.strip().lower())
        if level:
            stmt = stmt.where(ExamQuestion.level == level)
    if not include_retired:
        stmt = stmt.where(_active_filter())
    rows = session.exec(stmt.order_by(ExamQuestion.created_at.desc()).offset(skip).limit(limit)).all()
    return [AdminQuestion.model_validate(q) for q in rows]


def retire(session: Session, question_id: UUID) -> AdminQuestion:
    """A retired question is never served again (R5.2). Attempts that already had it keep it."""
    question = session.get(ExamQuestion, question_id)
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    if question.retired_at is None:
        question.retired_at = clock.now()
        session.add(question)
        session.commit()
        session.refresh(question)
    return AdminQuestion.model_validate(question)


def bank_levels(session: Session) -> list[BankLevel]:
    counts: dict[tuple[str, EducationLevel | None], int] = defaultdict(int)
    for key, level, n in session.exec(
        select(ExamQuestion.subject_key, ExamQuestion.level, func.count())
        .where(_active_filter()).group_by(ExamQuestion.subject_key, ExamQuestion.level)
    ).all():
        counts[(key, level)] = n
    return [BankLevel(subject=t.subject, level=t.level, active=counts[(t.subject_key, t.level)], target=t.target)
            for t in (GENERAL, *tags_in_use(session))]
