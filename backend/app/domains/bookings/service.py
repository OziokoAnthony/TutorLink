"""Booking lifecycle (spec 1 R2), billing periods (R3.5) and paying them from the balance (R3.3).

Functions that depend on the time take `now`, so the background jobs and the tests can move the clock.
"""

from collections.abc import Callable
from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core import clock
from app.core.clock import WAT, at_wat, money, today_wat
from app.domains.auth import photos
from app.domains.auth import service as auth_service
from app.domains.auth.models import User, UserRole
from app.domains.bookings import schedule
from app.domains.bookings.models import (
    HOLDS_SLOTS,
    Booking,
    BookingAdminView,
    BookingClose,
    BookingCreate,
    BookingParentView,
    BookingPeriod,
    BookingSlot,
    BookingStatus,
    BookingTutorView,
    PeriodStatus,
    PeriodView,
    TutorAvailability,
    TutorSlotRead,
)
from app.domains.fees import service as fees_service
from app.domains.job_posts import sync as job_sync
from app.domains.lessons.models import EarningStatus, Lesson, LessonStatus
from app.domains.notifications import service as notifications
from app.domains.payments import service as payments
from app.domains.payments.models import EntryKind, Refund, RefundReason, RefundRead, RefundStatus
from app.domains.tutors import service as tutor_service
from app.domains.tutors.models import TutorOffer, WeeklyTime

REQUEST_TTL = timedelta(hours=72)  # tutor must answer within 72 h (spec 1 R2.4)
CANCEL_NOTICE = timedelta(hours=48)  # lessons at least this far away are refunded on cancellation (R2.8)
PAUSE_LIMIT = timedelta(days=7)  # a paused booking ends after 7 days (R3.5)
PAYOUT_AFTER = timedelta(hours=48)  # tutor is paid 48 h after the period's last lesson (R6.2)
REMIND_BEFORE = timedelta(hours=24)  # reminder 24 h before a payment deadline (R3.5)

DAY_NAMES = notifications.DAY_NAMES


# ---------- Reading ----------

def _slots(session: Session, booking_ids: list[UUID]) -> dict[UUID, list[BookingSlot]]:
    grouped: dict[UUID, list[BookingSlot]] = {bid: [] for bid in booking_ids}
    if booking_ids:
        for slot in session.exec(select(BookingSlot).where(BookingSlot.booking_id.in_(booking_ids))
                                 .order_by(BookingSlot.day_of_week, BookingSlot.start_time)).all():
            grouped[slot.booking_id].append(slot)
    return grouped


def _periods(session: Session, booking_ids: list[UUID]) -> dict[UUID, list[BookingPeriod]]:
    grouped: dict[UUID, list[BookingPeriod]] = {bid: [] for bid in booking_ids}
    if booking_ids:
        for period in session.exec(select(BookingPeriod).where(BookingPeriod.booking_id.in_(booking_ids))
                                   .order_by(BookingPeriod.starts_on)).all():
            grouped[period.booking_id].append(period)
    return grouped


def _rates(session: Session, booking: Booking) -> tuple[Decimal, Decimal]:
    """The booking's fee rates: copied at acceptance, or today's rates while it's still a request."""
    if booking.parent_fee_rate is not None and booking.tutor_fee_rate is not None:
        return booking.parent_fee_rate, booking.tutor_fee_rate
    fees = fees_service.current(session)
    return fees.parent_fee_rate, fees.tutor_fee_rate


def _views(session: Session, bookings: list[Booking], view):
    ids = [b.id for b in bookings]
    slots = _slots(session, ids)
    periods = _periods(session, ids)
    people = [b.parent_id for b in bookings] + [b.tutor_id for b in bookings]
    names = auth_service.full_names(session, people)
    pictures = photos.urls_for(session, people)
    result = []
    for b in bookings:
        parent_rate, tutor_rate = _rates(session, b)
        parent_price = fees_service.parent_price(b.price, parent_rate)
        earning = fees_service.tutor_earning(b.price, tutor_rate)
        extra = {
            "slots": [WeeklyTime.model_validate(s) for s in slots[b.id]],
            "parent_name": names.get(b.parent_id), "tutor_name": names.get(b.tutor_id),
            "parent_photo_url": pictures.get(b.parent_id), "tutor_photo_url": pictures.get(b.tutor_id),
            "parent_price_per_lesson": parent_price,
            "tutor_fee_rate": tutor_rate, "tutor_earning_per_lesson": earning,
            "parent_fee_rate": parent_rate, "platform_margin_per_lesson": money(parent_price - earning),
            "periods": [PeriodView.model_validate(p) for p in periods[b.id]],
        }
        # Each view model only declares the fields its reader may see; the rest are dropped here.
        result.append(view.model_validate(b, update={k: v for k, v in extra.items() if k in view.model_fields}))
    return result


def _get(session: Session, booking_id: UUID, *, lock: bool = False) -> Booking:
    stmt = select(Booking).where(Booking.id == booking_id)
    if lock:
        stmt = stmt.with_for_update()
    booking = session.exec(stmt).first()
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


def view_for(session: Session, user: User, booking: Booking):
    if user.role == UserRole.admin:
        return _views(session, [booking], BookingAdminView)[0]
    if user.id == booking.parent_id:
        return _views(session, [booking], BookingParentView)[0]
    if user.id == booking.tutor_id:
        return _views(session, [booking], BookingTutorView)[0]
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own bookings")


def get_booking(session: Session, user: User, booking_id: UUID):
    return view_for(session, user, _get(session, booking_id))


def list_parent_bookings(session: Session, parent: User) -> list[BookingParentView]:
    rows = session.exec(select(Booking).where(Booking.parent_id == parent.id).order_by(Booking.created_at.desc())).all()
    return _views(session, list(rows), BookingParentView)


def list_tutor_bookings(session: Session, tutor: User) -> list[BookingTutorView]:
    rows = session.exec(select(Booking).where(Booking.tutor_id == tutor.id).order_by(Booking.created_at.desc())).all()
    return _views(session, list(rows), BookingTutorView)


def list_all_bookings(session: Session, status_: BookingStatus | None, skip: int, limit: int) -> list[BookingAdminView]:
    stmt = select(Booking).order_by(Booking.created_at.desc()).offset(skip).limit(limit)
    if status_:
        stmt = stmt.where(Booking.status == status_)
    return _views(session, list(session.exec(stmt).all()), BookingAdminView)


def _minus(window: WeeklyTime, busy: list[BookingSlot]) -> list[TutorSlotRead]:
    """The parts of a weekly window not covered by any busy slot."""
    pieces = [(window.start_time, window.end_time)]
    for b in sorted((b for b in busy if b.day_of_week == window.day_of_week), key=lambda b: b.start_time):
        cut = []
        for start, end in pieces:
            if b.end_time <= start or b.start_time >= end:
                cut.append((start, end))
                continue
            if start < b.start_time:
                cut.append((start, b.start_time))
            if b.end_time < end:
                cut.append((b.end_time, end))
        pieces = cut
    return [TutorSlotRead(day_of_week=window.day_of_week, start_time=s, end_time=e) for s, e in pieces]


def tutor_availability(session: Session, tutor_user_id: UUID, now: datetime | None = None) -> TutorAvailability:
    """The tutor's booked weekly times, their open times, and whether they're teaching now."""
    now = now or clock.now()
    if tutor_service.get_approved_profile(session, tutor_user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    busy = sorted(_taken_slots(session, tutor_user_id), key=lambda s: (s.day_of_week, s.start_time))
    windows = {(w.day_of_week, w.start_time, w.end_time): w
               for offer in tutor_service.list_offers_of(session, tutor_user_id) for w in offer.windows}
    free = [piece for w in sorted(windows.values(), key=lambda w: (w.day_of_week, w.start_time))
            for piece in _minus(w, busy)]
    teaching = session.exec(select(Lesson.id).where(
        Lesson.tutor_id == tutor_user_id, Lesson.starts_at <= now, Lesson.ends_at > now,
        Lesson.status.in_((LessonStatus.confirmed, LessonStatus.reported)),
    )).first()
    return TutorAvailability(in_session_now=teaching is not None,
                             busy=[TutorSlotRead.model_validate(s) for s in busy], free=free)


# ---------- Requesting ----------

def _taken_slots(session: Session, tutor_id: UUID, exclude: UUID | None = None) -> list[BookingSlot]:
    stmt = (select(BookingSlot).join(Booking, Booking.id == BookingSlot.booking_id)
            .where(Booking.tutor_id == tutor_id, Booking.status.in_(HOLDS_SLOTS)))
    if exclude is not None:
        stmt = stmt.where(Booking.id != exclude)
    return list(session.exec(stmt).all())


def _check_no_clash(new_slots, taken) -> None:
    for slot in new_slots:
        if any(schedule.overlaps(slot, other) for other in taken):
            raise HTTPException(status.HTTP_409_CONFLICT, "Tutor already has a session at this time.")


def request_booking(session: Session, parent: User, data: BookingCreate, now: datetime | None = None) -> BookingParentView:
    now = now or clock.now()
    if parent.photo_key is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add a profile picture before booking a tutor")
    # Lock the tutor's row so two bookings can't both pass the clash check.
    tutor = session.exec(select(User).where(User.id == data.tutor_id, User.role == UserRole.tutor,
                                            User.is_active == True).with_for_update()).first()  # noqa: E712
    if tutor is None or tutor_service.get_approved_profile(session, tutor.id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tutor not found")
    offer = tutor_service.get_offer(session, data.offer_id)
    if offer is None or session.get(TutorOffer, offer.id).tutor_id != tutor.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer not found")

    offered = {s.lower(): s for s in offer.subjects}
    missing = [s for s in data.subjects if s.lower() not in offered]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            f"This offer doesn't include: {', '.join(missing)}")
    for slot in data.slots:
        if not any(schedule.within(slot, window) for window in offer.windows):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"{DAY_NAMES[slot.day_of_week]} {slot.start_time:%H:%M}-{slot.end_time:%H:%M} "
                                "is outside the tutor's available times for this offer")
    for i, slot in enumerate(data.slots):
        if any(schedule.overlaps(slot, other) for other in data.slots[i + 1:]):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Two of the lesson times overlap")
    if data.start_date < today_wat(now):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start_date can't be in the past")
    if schedule.plan_period(data.slots, data.billing_period, data.start_date, data.end_date) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "There are no lessons between these dates")
    _check_no_clash(data.slots, _taken_slots(session, tutor.id))

    booking = Booking(
        parent_id=parent.id, tutor_id=tutor.id, offer_id=offer.id,
        subjects=[offered[s.lower()] for s in data.subjects], level=offer.level, mode=data.mode,
        billing_period=data.billing_period, start_date=data.start_date, end_date=data.end_date,
        price=offer.price, child_strengths=data.child_strengths, child_weaknesses=data.child_weaknesses,
        created_at=now, updated_at=now,
    )
    session.add(booking)
    session.flush()
    for slot in data.slots:
        session.add(BookingSlot(booking_id=booking.id, **slot.model_dump()))
    notifications.notify(
        session, tutor.id, "New booking request",
        f"You have a new request for {', '.join(booking.subjects)}. Please accept or decline it within 72 hours.",
        "/dashboard/tutor/bookings",
    )
    session.commit()
    session.refresh(booking)
    return _views(session, [booking], BookingParentView)[0]


# ---------- Tutor's answer ----------

def accept(session: Session, tutor: User, booking_id: UUID, now: datetime | None = None) -> BookingTutorView:
    now = now or clock.now()
    session.exec(select(User.id).where(User.id == tutor.id).with_for_update()).one()  # serialise clash checks
    booking = _get(session, booking_id, lock=True)
    if booking.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request isn't for you")
    if booking.status != BookingStatus.requested or now >= booking.created_at + REQUEST_TTL:
        raise HTTPException(status.HTTP_409_CONFLICT, "This request can no longer be accepted")
    slots = _slots(session, [booking.id])[booking.id]
    _check_no_clash(slots, _taken_slots(session, tutor.id, exclude=booking.id))
    _take(session, booking, slots, now)
    return _views(session, [booking], BookingTutorView)[0]


def _take(session: Session, booking: Booking, slots, now: datetime) -> None:
    """The booking is taken: fee rates are frozen, the first period becomes payable and the parent is
    told what to pay (spec 1 R2.5, R2.6). Commits, then pays the period if the balance covers it."""
    fees = fees_service.current(session)
    booking.parent_fee_rate = fees.parent_fee_rate
    booking.tutor_fee_rate = fees.tutor_fee_rate
    # The first lesson must be more than 24 h away so the parent can pay in time (spec 1 R2.6).
    plan = schedule.plan_period(slots, booking.billing_period, max(booking.start_date, today_wat(now)),
                                booking.end_date, not_before=now + schedule.PAY_BEFORE)
    if plan is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No lessons are left before the booking's end date")
    period = _add_period(session, booking, plan)
    booking.status = BookingStatus.accepted
    booking.responded_at = now
    session.add(booking)

    account = payments.ensure_virtual_account(session, booking.parent_id)
    notifications.notify(
        session, booking.parent_id, "Your booking has been taken",
        f"Your tutor accepted your booking for {', '.join(booking.subjects)}.\n"
        f"Please pay {notifications.naira(period.amount)} for the first "
        f"{period.lesson_count} lesson(s) before {_when(period.due_at)}.\n{payments.account_text(account)}",
        "/dashboard/parent/wallet",
    )
    session.commit()
    pay_due_periods(session, booking.parent_id, now)
    session.refresh(booking)


def book_from_job(session: Session, *, parent_id: UUID, tutor_id: UUID, job_id: UUID, subjects: list[str],
                  level, mode, billing_period, start_date, end_date, price: Decimal, child_strengths: str,
                  child_weaknesses: str, slots: list[WeeklyTime], now: datetime,
                  on_created: Callable[[Booking], None]) -> Booking:
    """A parent chose a job applicant: the booking starts already taken, awaiting payment (spec 2 R3.2).
    The caller has locked and checked the job; this checks the tutor's time, calls `on_created` once the
    booking row exists (so the job's changes commit with it), then commits."""
    session.exec(select(User.id).where(User.id == tutor_id).with_for_update()).one()  # serialise clash checks
    _check_no_clash(slots, _taken_slots(session, tutor_id))
    booking = Booking(
        parent_id=parent_id, tutor_id=tutor_id, job_id=job_id, subjects=subjects, level=level, mode=mode,
        billing_period=billing_period, start_date=max(start_date, today_wat(now)), end_date=end_date, price=price,
        child_strengths=child_strengths, child_weaknesses=child_weaknesses, created_at=now, updated_at=now,
    )
    session.add(booking)
    session.flush()
    rows = [BookingSlot(booking_id=booking.id, **slot.model_dump()) for slot in slots]
    session.add_all(rows)
    session.flush()
    on_created(booking)
    _take(session, booking, rows, now)
    return booking


def parent_view(session: Session, booking: Booking) -> BookingParentView:
    return _views(session, [booking], BookingParentView)[0]


def taken_slots(session: Session, tutor_id: UUID) -> list[BookingSlot]:
    """The tutor's weekly times held by accepted, active or paused bookings (spec 1 R2.2)."""
    return _taken_slots(session, tutor_id)


def decline(session: Session, tutor: User, booking_id: UUID, data: BookingClose,
            now: datetime | None = None) -> BookingTutorView:
    now = now or clock.now()
    booking = _get(session, booking_id, lock=True)
    if booking.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This request isn't for you")
    if booking.status != BookingStatus.requested:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a pending request can be declined")
    _close(session, booking, BookingStatus.declined, now, data.note)
    session.add(booking)
    notifications.notify(session, booking.parent_id, "Booking declined",
                         "The tutor can't take your booking request. You can book another tutor.",
                         "/tutors")
    session.commit()
    return _views(session, [booking], BookingTutorView)[0]


# ---------- Ending ----------

def _close(session: Session, booking: Booking, new_status: BookingStatus, now: datetime,
           note: str | None = None) -> None:
    booking.status = new_status
    booking.closed_at = now
    booking.close_note = note
    job_sync.booking_closed(session, booking)  # its job reopens or completes (spec 2 R3.4, R3.5)


def _void_unpaid_periods(session: Session, booking: Booking) -> None:
    for period in session.exec(select(BookingPeriod).where(BookingPeriod.booking_id == booking.id,
                                                           BookingPeriod.status == PeriodStatus.due)).all():
        period.status = PeriodStatus.void
        session.add(period)


def _future_lessons(session: Session, booking: Booking, after: datetime) -> list[Lesson]:
    return list(session.exec(
        select(Lesson).where(Lesson.booking_id == booking.id, Lesson.status == LessonStatus.confirmed,
                             Lesson.starts_at >= after).order_by(Lesson.starts_at)
    ).all())


def cancel(session: Session, parent: User, booking_id: UUID, data: BookingClose,
           now: datetime | None = None) -> BookingParentView:
    """Parent cancels. Paid lessons at least 48 h away are cancelled and a refund of their agreed price
    (fee excluded) goes to the admin for approval; sooner lessons still happen (spec 1 R2.8, R5.4)."""
    now = now or clock.now()
    booking = _get(session, booking_id, lock=True)
    if booking.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only cancel your own bookings")
    if booking.status not in (BookingStatus.requested, BookingStatus.accepted,
                              BookingStatus.active, BookingStatus.paused):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Booking is already {booking.status.value}")

    _void_unpaid_periods(session, booking)
    refunded = _future_lessons(session, booking, now + CANCEL_NOTICE)
    for lesson in refunded:
        lesson.status = LessonStatus.cancelled
        lesson.earning_status = EarningStatus.void
        session.add(lesson)
    if refunded:
        refund = Refund(parent_id=booking.parent_id, booking_id=booking.id, reason=RefundReason.cancellation,
                        lesson_count=len(refunded), amount=money(sum((l.price for l in refunded), Decimal(0))),
                        status=RefundStatus.pending)
        session.add(refund)
        for admin_id in payments.admin_ids(session):
            notifications.notify(session, admin_id, "Refund to approve",
                                 f"A parent cancelled a booking: {len(refunded)} lesson(s), "
                                 f"{notifications.naira(refund.amount)} to refund.", "/admin/refunds", email=False)
    _close(session, booking, BookingStatus.cancelled, now, data.note)
    session.add(booking)
    kept = len(_future_lessons(session, booking, now))
    notifications.notify(
        session, booking.tutor_id, "Booking cancelled",
        "The parent cancelled the booking." + (f" {kept} lesson(s) within the next 48 hours still go ahead." if kept else ""),
        "/dashboard/tutor/bookings",
    )
    session.commit()
    return _views(session, [booking], BookingParentView)[0]


def end(session: Session, user: User, booking_id: UUID, data: BookingClose, now: datetime | None = None):
    """Either side stops the booking renewing: lessons already paid for still happen, then it ends
    (spec 1 R2.9). A request or unpaid booking closes at once."""
    now = now or clock.now()
    booking = _get(session, booking_id, lock=True)
    if user.id not in (booking.parent_id, booking.tutor_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only end your own bookings")
    if booking.status == BookingStatus.requested:
        if user.id == booking.tutor_id:
            return decline(session, user, booking_id, data, now)
        _close(session, booking, BookingStatus.cancelled, now, data.note)
    elif booking.status == BookingStatus.accepted:
        _void_unpaid_periods(session, booking)
        _close(session, booking, BookingStatus.ended, now, data.note)
    elif booking.status in (BookingStatus.active, BookingStatus.paused):
        _void_unpaid_periods(session, booking)
        last_paid = session.exec(select(BookingPeriod).where(BookingPeriod.booking_id == booking.id,
                                                             BookingPeriod.status == PeriodStatus.paid)
                                 .order_by(BookingPeriod.starts_on.desc())).first()
        booking.end_date = last_paid.ends_on if last_paid else today_wat(now)
        booking.close_note = data.note
        if last_paid is None or last_paid.last_lesson_end_at <= now:
            _close(session, booking, BookingStatus.ended, now, data.note)
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Booking is already {booking.status.value}")
    session.add(booking)
    other = booking.tutor_id if user.id == booking.parent_id else booking.parent_id
    notifications.notify(session, other, "Booking ending",
                         "The booking won't renew. Lessons already paid for still go ahead." if booking.status
                         in (BookingStatus.active, BookingStatus.paused) else "The booking has been closed.",
                         "/dashboard")
    session.commit()
    return view_for(session, user, booking)


# ---------- Periods and payment ----------

def _when(moment: datetime) -> str:
    local = moment.astimezone(WAT)
    return f"{notifications.date_text(local.date())} at {local:%H:%M}"


def _add_period(session: Session, booking: Booking, plan: schedule.PeriodPlan) -> BookingPeriod:
    parent_rate, _ = _rates(session, booking)
    period = BookingPeriod(
        booking_id=booking.id, parent_id=booking.parent_id, starts_on=plan.starts_on, ends_on=plan.ends_on,
        lesson_count=len(plan.lessons),
        amount=money(fees_service.parent_price(booking.price, parent_rate) * len(plan.lessons)),
        first_lesson_at=plan.first_lesson_at, last_lesson_end_at=plan.last_lesson_end_at, due_at=plan.due_at,
    )
    session.add(period)
    session.flush()
    return period


def _create_lessons(session: Session, booking: Booking, period: BookingPeriod) -> int:
    parent_rate, tutor_rate = _rates(session, booking)
    slots = _slots(session, [booking.id])[booking.id]
    occurrences = [o for o in schedule.occurrences(slots, period.starts_on, period.ends_on)
                   if o.starts_at >= period.first_lesson_at]
    for o in occurrences:
        session.add(Lesson(
            booking_id=booking.id, period_id=period.id, parent_id=booking.parent_id, tutor_id=booking.tutor_id,
            lesson_date=o.lesson_date, start_time=o.start_time, end_time=o.end_time,
            starts_at=o.starts_at, ends_at=o.ends_at, price=booking.price,
            parent_price=fees_service.parent_price(booking.price, parent_rate),
            tutor_earning=fees_service.tutor_earning(booking.price, tutor_rate),
            payout_due_at=period.last_lesson_end_at + PAYOUT_AFTER,
        ))
    return len(occurrences)


def pay_due_periods(session: Session, parent_id: UUID, now: datetime | None = None) -> int:
    """Pays the parent's due periods from their balance, oldest deadline first, while it covers them.
    Paying a period puts its lessons on the timetable, already confirmed (spec 1 R2.7). Commits."""
    now = now or clock.now()
    payments.lock_parent(session, parent_id)
    available = payments.balance(session, parent_id)
    paid = 0
    due = session.exec(select(BookingPeriod).where(BookingPeriod.parent_id == parent_id,
                                                   BookingPeriod.status == PeriodStatus.due,
                                                   BookingPeriod.due_at > now)
                       .order_by(BookingPeriod.due_at)).all()
    for period in due:
        if period.amount > available:
            break
        booking = _get(session, period.booking_id, lock=True)
        entry = payments.add_entry(session, parent_id, EntryKind.period_payment, -period.amount,
                           f"{period.lesson_count} lesson(s): {', '.join(booking.subjects)}, "
                           f"{period.starts_on:%d %b} - {period.ends_on:%d %b %Y}", period_id=period.id)
        available -= period.amount
        period.status = PeriodStatus.paid
        period.paid_at = now
        session.add(period)
        count = _create_lessons(session, booking, period)
        booking.status = BookingStatus.active
        booking.paused_at = None
        session.add(booking)
        paid += 1
        notifications.notify(session, parent_id, "Lessons confirmed",
                             f"{count} lesson(s) from {notifications.date_text(period.starts_on)} are paid for "
                             f"and confirmed. {notifications.naira(period.amount)} was taken from your balance; "
                             "your receipt is ready.", f"/receipts/wallet/{entry.id}")
        notifications.notify(session, booking.tutor_id, "Lessons confirmed",
                             f"{count} lesson(s) from {notifications.date_text(period.starts_on)} are paid for "
                             "and confirmed on your timetable.", "/dashboard/tutor/lessons")
    session.commit()
    return paid


# ---------- Refunds (admin) ----------

def _refund_reads(session: Session, refunds: list[Refund]) -> list[RefundRead]:
    names = auth_service.full_names(session, [r.parent_id for r in refunds])
    return [RefundRead.model_validate(r, update={"parent_name": names.get(r.parent_id)}) for r in refunds]


def list_refunds(session: Session, status_: RefundStatus | None) -> list[RefundRead]:
    stmt = select(Refund).order_by(Refund.created_at.desc())
    if status_:
        stmt = stmt.where(Refund.status == status_)
    return _refund_reads(session, list(session.exec(stmt).all()))


def decide_refund(session: Session, admin: User, refund_id: UUID, approve: bool, note: str | None,
                  now: datetime | None = None) -> RefundRead:
    now = now or clock.now()
    refund = session.exec(select(Refund).where(Refund.id == refund_id).with_for_update()).first()
    if refund is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Refund not found")
    if refund.status != RefundStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Refund is already {refund.status.value}")
    refund.status = RefundStatus.approved if approve else RefundStatus.rejected
    refund.note = note
    refund.decided_by = admin.id
    refund.decided_at = now
    session.add(refund)
    if approve:
        payments.lock_parent(session, refund.parent_id)
        entry = payments.add_entry(session, refund.parent_id, EntryKind.refund, refund.amount,
                                   f"Refund for {refund.lesson_count} cancelled lesson(s)", refund_id=refund.id)
        notifications.notify(session, refund.parent_id, "Refund added to your balance",
                             f"{notifications.naira(refund.amount)} for {refund.lesson_count} cancelled lesson(s) "
                             "is now in your TutorLink balance.", f"/receipts/wallet/{entry.id}")
    else:
        notifications.notify(session, refund.parent_id, "Refund not approved",
                             f"Your refund request wasn't approved.{' Note: ' + note if note else ''}",
                             "/dashboard/parent/wallet")
    session.commit()
    if approve:
        pay_due_periods(session, refund.parent_id, now)
    session.refresh(refund)
    return _refund_reads(session, [refund])[0]


# ---------- Background jobs ----------

def expire_requests(session: Session, now: datetime) -> int:
    rows = session.exec(select(Booking).where(Booking.status == BookingStatus.requested,
                                              Booking.created_at <= now - REQUEST_TTL).with_for_update()).all()
    for booking in rows:
        _close(session, booking, BookingStatus.expired, now)
        session.add(booking)
        notifications.notify(session, booking.parent_id, "Booking request expired",
                             "The tutor didn't answer within 72 hours. You can book another tutor.", "/tutors")
    session.commit()
    return len(rows)


def create_next_periods(session: Session, now: datetime) -> int:
    """Once a booking's latest period has started, its next one becomes payable (spec 1 R3.5)."""
    created = 0
    rows = session.exec(select(Booking).where(Booking.status.in_((BookingStatus.active, BookingStatus.paused)))
                        .with_for_update()).all()
    for booking in rows:
        latest = session.exec(select(BookingPeriod).where(BookingPeriod.booking_id == booking.id)
                              .order_by(BookingPeriod.starts_on.desc())).first()
        if latest is None or now < at_wat(latest.starts_on, time(0)):
            continue
        slots = _slots(session, [booking.id])[booking.id]
        plan = schedule.plan_period(slots, booking.billing_period, latest.ends_on + timedelta(days=1), booking.end_date)
        if plan is None:
            continue
        period = _add_period(session, booking, plan)
        account = payments.get_virtual_account(session, booking.parent_id)
        notifications.notify(
            session, booking.parent_id, "Next lessons ready to pay",
            f"Please pay {notifications.naira(period.amount)} for {period.lesson_count} lesson(s) from "
            f"{notifications.date_text(period.starts_on)} before {_when(period.due_at)}.\n{payments.account_text(account)}",
            "/dashboard/parent/wallet",
        )
        created += 1
    session.commit()
    return created


def remind_due_periods(session: Session, now: datetime) -> int:
    rows = session.exec(select(BookingPeriod).where(BookingPeriod.status == PeriodStatus.due,
                                                    BookingPeriod.reminder_sent_at.is_(None),
                                                    BookingPeriod.due_at > now,
                                                    BookingPeriod.due_at <= now + REMIND_BEFORE)).all()
    for period in rows:
        account = payments.get_virtual_account(session, period.parent_id)
        notifications.notify(session, period.parent_id, "Payment due in 24 hours",
                             f"{notifications.naira(period.amount)} is due before {_when(period.due_at)}, or those "
                             f"lessons won't go ahead.\n{payments.account_text(account)}", "/dashboard/parent/wallet")
        period.reminder_sent_at = now
        session.add(period)
    session.commit()
    return len(rows)


def handle_missed_deadlines(session: Session, now: datetime) -> int:
    """Unpaid at the deadline: the first period releases the booking, a later one pauses it."""
    rows = session.exec(select(BookingPeriod).where(BookingPeriod.status == PeriodStatus.due,
                                                    BookingPeriod.due_at <= now)).all()
    for period in rows:
        booking = _get(session, period.booking_id, lock=True)
        if booking.status == BookingStatus.accepted:
            period.status = PeriodStatus.expired
            _close(session, booking, BookingStatus.released, now)
            text = "The first payment wasn't made in time, so the booking was released."
        else:
            period.status = PeriodStatus.missed
            if booking.status == BookingStatus.active:
                booking.status = BookingStatus.paused
                booking.paused_at = now
            text = (f"Lessons from {notifications.date_text(period.starts_on)} weren't paid for in time, so they "
                    "won't go ahead. Pay the next lessons to continue; the booking ends after 7 days.")
        session.add(period)
        session.add(booking)
        for user_id in (booking.parent_id, booking.tutor_id):
            notifications.notify(session, user_id, "Booking " + booking.status.value, text, "/dashboard")
    session.commit()
    return len(rows)


def end_finished_bookings(session: Session, now: datetime) -> int:
    """Ends bookings paused for 7 days, and bookings whose last lesson is over with no more to come."""
    ended = 0
    paused = session.exec(select(Booking).where(Booking.status == BookingStatus.paused,
                                                Booking.paused_at <= now - PAUSE_LIMIT).with_for_update()).all()
    for booking in paused:
        _void_unpaid_periods(session, booking)
        _close(session, booking, BookingStatus.ended, now, "Ended after 7 days without payment")
        session.add(booking)
        for user_id in (booking.parent_id, booking.tutor_id):
            notifications.notify(session, user_id, "Booking ended",
                                 "The booking ended because it wasn't paid for 7 days.", "/dashboard")
        ended += 1
    active = session.exec(select(Booking).where(Booking.status == BookingStatus.active).with_for_update()).all()
    for booking in active:
        latest = session.exec(select(BookingPeriod).where(BookingPeriod.booking_id == booking.id)
                              .order_by(BookingPeriod.starts_on.desc())).first()
        if latest is None or latest.status != PeriodStatus.paid or latest.last_lesson_end_at > now:
            continue
        slots = _slots(session, [booking.id])[booking.id]
        if schedule.plan_period(slots, booking.billing_period, latest.ends_on + timedelta(days=1),
                                booking.end_date) is not None:
            continue
        _close(session, booking, BookingStatus.ended, now, booking.close_note)
        session.add(booking)
        for user_id in (booking.parent_id, booking.tutor_id):
            notifications.notify(session, user_id, "Booking completed", "All lessons of the booking are done.",
                                 "/dashboard")
        ended += 1
    session.commit()
    return ended


def pay_all_due(session: Session, now: datetime) -> int:
    """Retries paying due periods for every parent who has any (e.g. after a returned withdrawal)."""
    parents = session.exec(select(BookingPeriod.parent_id).where(BookingPeriod.status == PeriodStatus.due,
                                                                 BookingPeriod.due_at > now).distinct()).all()
    return sum(pay_due_periods(session, parent_id, now) for parent_id in parents)
