from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.payments import service
from app.domains.payments.models import (
    AdminDecision,
    BankRead,
    ParentReceipt,
    TransferStatus,
    VirtualAccountRead,
    WalletRead,
    WithdrawalAdminRead,
    WithdrawalCreate,
    WithdrawalRead,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])
banks_router = APIRouter(prefix="/banks", tags=["wallet"])
admin_router = APIRouter(prefix="/admin/withdrawals", tags=["admin"])

parent_only = require_roles([UserRole.parent])
admin_only = require_roles([UserRole.admin])


@router.get("/me", response_model=WalletRead)
def my_wallet(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.wallet(session, parent)


@router.post("/me/account-number", response_model=VirtualAccountRead)
def request_account_number(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.request_virtual_account(session, parent)


@router.post("/me/withdrawals", response_model=WithdrawalRead, status_code=status.HTTP_201_CREATED)
def request_withdrawal(data: WithdrawalCreate, parent: User = Depends(parent_only),
                       session: Session = Depends(get_session)):
    return service.request_withdrawal(session, parent, data)


@router.get("/me/withdrawals", response_model=list[WithdrawalRead])
def my_withdrawals(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.my_withdrawals(session, parent)


@router.get("/me/receipts/{entry_id}", response_model=ParentReceipt)
def receipt(entry_id: UUID, parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.parent_receipt(session, parent, entry_id)


@banks_router.get("", response_model=list[BankRead])
def banks(user: User = Depends(get_current_user)):
    return service.list_banks()


@admin_router.get("", response_model=list[WithdrawalAdminRead])
def withdrawals(status_: TransferStatus | None = Query(None, alias="status"), admin: User = Depends(admin_only),
                session: Session = Depends(get_session)):
    return service.admin_withdrawals(session, status_)


@admin_router.post("/{withdrawal_id}/send", response_model=WithdrawalAdminRead)
def send(withdrawal_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.send_withdrawal(session, admin, withdrawal_id)


@admin_router.post("/{withdrawal_id}/mark-paid", response_model=WithdrawalAdminRead)
def mark_paid(withdrawal_id: UUID, data: AdminDecision, admin: User = Depends(admin_only),
              session: Session = Depends(get_session)):
    return service.mark_withdrawal_paid(session, admin, withdrawal_id, data.note)


@admin_router.post("/{withdrawal_id}/reject", response_model=WithdrawalAdminRead)
def reject(withdrawal_id: UUID, data: AdminDecision, admin: User = Depends(admin_only),
           session: Session = Depends(get_session)):
    return service.reject_withdrawal(session, admin, withdrawal_id, data.note)
