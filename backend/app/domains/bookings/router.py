from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.bookings import service
from app.domains.bookings.models import (
    BookingAdminView,
    BookingClose,
    BookingCreate,
    BookingParentView,
    BookingStatus,
    BookingTutorView,
    MeetingLinkIn,
    TutorAvailability,
)
from app.domains.payments.models import AdminDecision, RefundRead, RefundStatus

router = APIRouter(prefix="/bookings", tags=["bookings"])
tutor_router = APIRouter(prefix="/tutors", tags=["bookings"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

parent_only = require_roles([UserRole.parent])
tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])

AnyView = BookingParentView | BookingTutorView | BookingAdminView


@router.post("", response_model=BookingParentView, status_code=status.HTTP_201_CREATED)
def request_booking(data: BookingCreate, parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.request_booking(session, parent, data)


@router.get("/me", response_model=list[BookingParentView])
def my_bookings(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.list_parent_bookings(session, parent)


@router.get("/tutor/me", response_model=list[BookingTutorView])
def my_tutor_bookings(tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.list_tutor_bookings(session, tutor)


@router.get("/{booking_id}", response_model=AnyView)
def get_booking(booking_id: UUID, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return service.get_booking(session, user, booking_id)


@router.post("/{booking_id}/accept", response_model=BookingTutorView)
def accept(booking_id: UUID, tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.accept(session, tutor, booking_id)


@router.post("/{booking_id}/decline", response_model=BookingTutorView)
def decline(booking_id: UUID, data: BookingClose, tutor: User = Depends(tutor_only),
            session: Session = Depends(get_session)):
    return service.decline(session, tutor, booking_id, data)


@router.put("/{booking_id}/meeting-link", response_model=BookingTutorView)
def set_meeting_link(booking_id: UUID, data: MeetingLinkIn, tutor: User = Depends(tutor_only),
                     session: Session = Depends(get_session)):
    """Online bookings: the tutor's video call link, shown to the parent once the first period is paid."""
    return service.set_meeting_link(session, tutor, booking_id, data)


@router.post("/{booking_id}/cancel", response_model=BookingParentView)
def cancel(booking_id: UUID, data: BookingClose, parent: User = Depends(parent_only),
           session: Session = Depends(get_session)):
    return service.cancel(session, parent, booking_id, data)


@router.post("/{booking_id}/end", response_model=AnyView)
def end(booking_id: UUID, data: BookingClose, user: User = Depends(get_current_user),
        session: Session = Depends(get_session)):
    return service.end(session, user, booking_id, data)


@tutor_router.get("/{tutor_id}/schedule", response_model=TutorAvailability)
def tutor_schedule(tutor_id: UUID, session: Session = Depends(get_session)):
    """Public: when the tutor is booked, when they're free, and whether they're teaching now."""
    return service.tutor_availability(session, tutor_id)


@admin_router.get("/bookings", response_model=list[BookingAdminView])
def all_bookings(status_: BookingStatus | None = Query(None, alias="status"), skip: int = Query(0, ge=0),
                 limit: int = Query(50, ge=1, le=200), admin: User = Depends(admin_only),
                 session: Session = Depends(get_session)):
    return service.list_all_bookings(session, status_, skip, limit)


@admin_router.get("/refunds", response_model=list[RefundRead])
def refunds(status_: RefundStatus | None = Query(None, alias="status"), admin: User = Depends(admin_only),
            session: Session = Depends(get_session)):
    return service.list_refunds(session, status_)


@admin_router.post("/refunds/{refund_id}/approve", response_model=RefundRead)
def approve_refund(refund_id: UUID, data: AdminDecision, admin: User = Depends(admin_only),
                   session: Session = Depends(get_session)):
    return service.decide_refund(session, admin, refund_id, True, data.note)


@admin_router.post("/refunds/{refund_id}/reject", response_model=RefundRead)
def reject_refund(refund_id: UUID, data: AdminDecision, admin: User = Depends(admin_only),
                  session: Session = Depends(get_session)):
    return service.decide_refund(session, admin, refund_id, False, data.note)
