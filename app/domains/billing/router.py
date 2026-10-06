from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.billing import service
from app.domains.billing.models import (
    GenerateInvoicesRequest,
    GenerateInvoicesResponse,
    InvoiceDetail,
    InvoiceRead,
    PaymentInitResponse,
)

router = APIRouter(prefix="/invoices", tags=["billing"])

parent_only = require_roles([UserRole.parent])
admin_only = require_roles([UserRole.admin])


@router.post("/generate", response_model=GenerateInvoicesResponse)
def generate_invoices(data: GenerateInvoicesRequest, admin: User = Depends(admin_only),
                      session: Session = Depends(get_session)):
    return service.generate_invoices(session, data)


@router.get("/me", response_model=list[InvoiceRead])
def my_invoices(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.list_my_invoices(session, parent)


@router.get("/{invoice_id}", response_model=InvoiceDetail)
def invoice_detail(invoice_id: UUID, parent: User = Depends(parent_only),
                   session: Session = Depends(get_session)):
    return service.get_invoice_detail(session, parent, invoice_id)


@router.post("/{invoice_id}/pay", response_model=PaymentInitResponse)
def pay_invoice(invoice_id: UUID, parent: User = Depends(parent_only),
                session: Session = Depends(get_session)):
    return service.pay_invoice(session, parent, invoice_id)
