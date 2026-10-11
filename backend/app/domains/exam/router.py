"""The qualifying exam (spec 4 R5): tutors take timed attempts; admins see attempts and manage the bank."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.exam import service
from app.domains.exam.models import (
    AdminAttempt,
    AdminQuestion,
    AnswersIn,
    AttemptResult,
    AttemptView,
    BankLevel,
    ExamStatus,
)
from app.domains.tutors.models import EducationLevel

router = APIRouter(prefix="/exam", tags=["exam"])
admin_router = APIRouter(prefix="/admin/exam", tags=["admin"])

tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.get("", response_model=ExamStatus)
def my_exam(user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """Whether the tutor passed, the attempt in progress, attempts left and past scores."""
    return service.get_status(session, user)


@router.post("/attempts", response_model=AttemptView)
def start_attempt(user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """Starts an attempt (or returns the one in progress): 20 questions, 30 minutes. 409 with
    "Your exam is being prepared" while the bank can't fill it yet (R5.8); 429 when locked (R5.7)."""
    return service.start_attempt(session, user)


@router.put("/attempts/{attempt_id}/answers", response_model=AttemptView)
def save_answers(attempt_id: UUID, data: AnswersIn, user: User = Depends(tutor_only),
                 session: Session = Depends(get_session)):
    """Saves answers (choice 0-3 per question position). Refused after the deadline (R5.4)."""
    return service.save_answers(session, user, attempt_id, data)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult)
def submit(attempt_id: UUID, user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """Scores the attempt: the score and pass/fail only, no correct answers (R5.5)."""
    return service.submit(session, user, attempt_id)


@admin_router.get("/attempts", response_model=list[AdminAttempt])
def attempts(tutor_id: UUID | None = None, admin: User = Depends(admin_only),
             session: Session = Depends(get_session)):
    """Every finished attempt's score, date and time taken, newest first (R5.9)."""
    return service.admin_attempts(session, tutor_id)


@admin_router.get("/questions", response_model=list[AdminQuestion])
def questions(subject: str | None = None, level: EducationLevel | None = None, general: bool = False,
              include_retired: bool = False, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
              admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Browse the bank, newest first: `?general=true` for general reasoning, or `?subject=&level=`."""
    return service.admin_questions(session, subject, level, general, include_retired, skip, limit)


@admin_router.post("/questions/{question_id}/retire", response_model=AdminQuestion)
def retire(question_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Retired questions are never served again (R5.2)."""
    return service.retire(session, question_id)


@admin_router.get("/bank", response_model=list[BankLevel])
def bank(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Active questions per tag against the target: 300 general, 200 per subject and level in use."""
    return service.bank_levels(session)
