from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.payouts import service
from app.domains.payouts.models import (
    BankAccountAdminView,
    BankAccountTutorView,
    BankAccountUpdate,
    BankOverride,
    EarningsSummary,
    PayoutCreate,
    PayoutDue,
    PayoutRead,
)

router = APIRouter(prefix="/earnings", tags=["earnings"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.get("/me", response_model=EarningsSummary)
def my_earnings(tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.earnings_summary(session, tutor)


@router.get("/me/bank-account", response_model=BankAccountTutorView | None)
def my_bank_account(tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.get_my_bank_account(session, tutor)


@router.put("/me/bank-account", response_model=BankAccountTutorView)
def set_bank_account(data: BankAccountUpdate, tutor: User = Depends(tutor_only),
                     session: Session = Depends(get_session)):
    return service.set_bank_account(session, tutor, data)


@admin_router.get("/payouts/due", response_model=list[PayoutDue])
def payouts_due(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.payouts_due(session)


@admin_router.get("/payouts", response_model=list[PayoutRead])
def payouts(tutor_id: UUID | None = None, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
            admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.list_payouts(session, tutor_id, skip, limit)


@admin_router.post("/payouts", response_model=PayoutRead, status_code=status.HTTP_201_CREATED)
def create_payout(data: PayoutCreate, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.create_payout(session, admin, data)


@admin_router.post("/tutors/{tutor_id}/bank-account/override", response_model=BankAccountAdminView)
def override_bank(tutor_id: UUID, data: BankOverride, admin: User = Depends(admin_only),
                  session: Session = Depends(get_session)):
    return service.override_bank_account(session, admin, tutor_id, data.note)
