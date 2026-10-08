from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.fees import service
from app.domains.fees.models import FeesRead, FeesUpdate

router = APIRouter(prefix="/admin/fees", tags=["admin"])

admin_only = require_roles([UserRole.admin])


@router.get("", response_model=FeesRead)
def get_fees(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.current(session)


@router.put("", response_model=FeesRead)
def update_fees(data: FeesUpdate, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.update(session, admin, data)
