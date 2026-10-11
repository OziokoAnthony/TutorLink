"""Feedback and the help assistant (spec 6)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.feedback import service
from app.domains.feedback.models import (
    FeedbackAdminView,
    FeedbackIn,
    FeedbackRead,
    FeedbackReplyIn,
    HelpChatIn,
    HelpChatOut,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])
help_router = APIRouter(prefix="/help", tags=["feedback"])
admin_router = APIRouter(prefix="/admin/feedback", tags=["admin"])

parent_or_tutor = require_roles([UserRole.parent, UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def send_feedback(data: FeedbackIn, user: User = Depends(parent_or_tutor), session: Session = Depends(get_session)):
    return service.send(session, user, data)


@router.get("/me", response_model=list[FeedbackRead])
def my_feedback(user: User = Depends(parent_or_tutor), session: Session = Depends(get_session)):
    return service.mine(session, user)


@help_router.post("/chat", response_model=HelpChatOut)
def help_chat(data: HelpChatIn, user: User = Depends(parent_or_tutor), session: Session = Depends(get_session)):
    """One answer from the help assistant to the conversation so far, which the browser keeps (R3.5)."""
    return HelpChatOut(reply=service.help_chat(session, user, data.messages))


@admin_router.get("", response_model=list[FeedbackAdminView])
def admin_feedback(answered: bool = Query(False), admin: User = Depends(admin_only),
                   session: Session = Depends(get_session)):
    return service.admin_list(session, answered)


@admin_router.post("/{feedback_id}/reply", response_model=FeedbackAdminView)
def reply(feedback_id: UUID, data: FeedbackReplyIn, admin: User = Depends(admin_only),
          session: Session = Depends(get_session)):
    return service.reply(session, admin, feedback_id, data)
