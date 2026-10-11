"""Feedback from parents and tutors, answered by admins, and the help assistant (spec 6)."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core import claude, clock
from app.domains.auth import limits
from app.domains.auth import service as auth_service
from app.domains.auth.models import User
from app.domains.feedback.models import (
    ChatMessage,
    Feedback,
    FeedbackAdminView,
    FeedbackIn,
    FeedbackKind,
    FeedbackRead,
    FeedbackReplyIn,
)
from app.domains.notifications import service as notifications
from app.domains.payments import service as payments

KIND_NAMES = {FeedbackKind.problem: "problem", FeedbackKind.suggestion: "suggestion",
              FeedbackKind.praise: "praise", FeedbackKind.question: "question"}


def _read(feedback: Feedback) -> FeedbackRead:
    return FeedbackRead.model_validate(feedback, from_attributes=True)


def send(session: Session, user: User, data: FeedbackIn) -> FeedbackRead:
    """R1.1, R1.3; admins are told in the app (R2.2)."""
    limits.hit(session, limits.FEEDBACK_USER, str(user.id))
    feedback = Feedback(user_id=user.id, kind=data.kind, message=data.message.strip(),
                        transcript=[m.model_dump(mode="json") for m in data.transcript] if data.transcript else None)
    session.add(feedback)
    for admin_id in payments.admin_ids(session):
        notifications.notify(session, admin_id, "New feedback",
                             f"A {user.role.value} sent a {KIND_NAMES[data.kind]}.", "/admin/feedback", email=False)
    session.commit()
    session.refresh(feedback)
    return _read(feedback)


def mine(session: Session, user: User) -> list[FeedbackRead]:
    """R1.2: newest first."""
    rows = session.exec(select(Feedback).where(Feedback.user_id == user.id).order_by(Feedback.created_at.desc()))
    return [_read(f) for f in rows.all()]


def admin_list(session: Session, answered: bool) -> list[FeedbackAdminView]:
    """R2.1: waiting oldest first, so it's answered in order; answered newest first."""
    stmt = select(Feedback)
    if answered:
        stmt = stmt.where(Feedback.replied_at.is_not(None)).order_by(Feedback.replied_at.desc())
    else:
        stmt = stmt.where(Feedback.replied_at.is_(None)).order_by(Feedback.created_at)
    rows = list(session.exec(stmt).all())
    users = {u.id: u for u in session.exec(select(User).where(User.id.in_({f.user_id for f in rows}))).all()}
    names = auth_service.full_names(session, users)
    return [FeedbackAdminView(**_read(f).model_dump(), user_id=f.user_id, user_name=names.get(f.user_id),
                              user_email=users[f.user_id].email, user_role=users[f.user_id].role.value)
            for f in rows]


def reply(session: Session, admin: User, feedback_id: UUID, data: FeedbackReplyIn) -> FeedbackAdminView:
    """R2.3: one reply, which reaches the sender in the app and by email."""
    feedback = session.get(Feedback, feedback_id, with_for_update=True)
    if feedback is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback not found")
    if feedback.replied_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This feedback has already been answered")
    feedback.reply = data.reply.strip()
    feedback.replied_at = clock.now()
    feedback.replied_by = admin.id
    session.add(feedback)
    sender = session.get(User, feedback.user_id)
    notifications.notify(session, feedback.user_id, "TutorLink replied to your feedback",
                         f"You wrote: {feedback.message[:200]}\n\nOur reply: {feedback.reply}",
                         f"/dashboard/{sender.role.value}/feedback")
    session.commit()
    return next(v for v in admin_list(session, answered=True) if v.id == feedback.id)


def help_chat(session: Session, user: User, messages: list[ChatMessage]) -> str:
    """R3: Claude's answer for the reader's role, or 503 when it isn't available (R3.6)."""
    if not claude.available():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The help assistant isn't available right now. Please send us feedback instead.")
    limits.hit(session, limits.HELP_USER, str(user.id))
    answer = claude.help_reply(user.role.value, [m.model_dump(mode="json") for m in messages])
    if answer is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The help assistant couldn't answer just now. Try again, or send this conversation "
                            "to the TutorLink team.")
    return answer
