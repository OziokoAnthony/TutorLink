from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.domains.auth.models import User
from app.domains.notifications import service
from app.domains.notifications.models import NotificationList

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=NotificationList)
def my_notifications(limit: int = Query(30, ge=1, le=100), user: User = Depends(get_current_user),
                     session: Session = Depends(get_session)):
    return service.list_mine(session, user.id, limit)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(notification_id: UUID, user: User = Depends(get_current_user),
              session: Session = Depends(get_session)):
    service.mark_read(session, user.id, notification_id)


@router.post("/me/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    service.mark_read(session, user.id, None)
