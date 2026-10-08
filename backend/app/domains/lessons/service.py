"""Lessons after they're paid: tutor reports, the parent's problem window, problems and their outcome
(spec 1 R4, R5). Functions that depend on the time take `now`."""

import logging
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core import clock, storage
from app.core.clock import at_wat
from app.domains.auth import service as auth_service
from app.domains.auth.models import User, UserRole
from app.domains.bookings import service as bookings_service
from app.domains.bookings.models import Booking, LessonMode
from app.domains.lessons.models import (
    EarningStatus,
    IssueCreate,
    IssueKind,
    IssueRead,
    IssueResolution,
    IssueResolve,
    Lesson,
    LessonAdminView,
    LessonIssue,
    LessonParentView,
    LessonReport,
    LessonStatus,
    LessonTutorView,
    RecordingLink,
    RecordingUpload,
    RecordingUploadIn,
)
from app.domains.notifications import service as notifications
from app.domains.payments import service as payments
from app.domains.payments.models import EntryKind, Refund, RefundReason, RefundStatus
from app.domains.reviews import service as review_service

REPORT_WITHIN = timedelta(hours=24)  # tutor reports within 24 h of the lesson's end (spec 1 R4.2)
PROBLEM_WINDOW = timedelta(hours=24)  # parent can report a problem for 24 h after the report (R4.3, R5.1)

# Lesson recordings (spec 3 R2)
RECORDING_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}
MAX_RECORDING_BYTES = 2 * 1024 ** 3  # 2 GB
UPLOAD_LINK_TTL = timedelta(hours=1)
VIEW_LINK_TTL = timedelta(minutes=15)
KEEP_RECORDINGS = timedelta(days=90)

logger = logging.getLogger(__name__)


# ---------- Reading ----------

def _latest_issues(session: Session, lesson_ids: list[UUID]) -> dict[UUID, LessonIssue]:
    """Each lesson's most recent issue (open or resolved)."""
    latest: dict[UUID, LessonIssue] = {}
    if lesson_ids:
        for issue in session.exec(select(LessonIssue).where(LessonIssue.lesson_id.in_(lesson_ids))
                                  .order_by(LessonIssue.created_at)).all():
            latest[issue.lesson_id] = issue
    return latest


def _issue_read(issue: LessonIssue) -> IssueRead:
    return IssueRead.model_validate(issue, update={"raised_automatically": issue.raised_by is None})


def _views(session: Session, lessons: list[Lesson], view):
    booking_ids = list({l.booking_id for l in lessons})
    bookings = {b.id: b for b in session.exec(select(Booking).where(Booking.id.in_(booking_ids))).all()} \
        if booking_ids else {}
    names = auth_service.full_names(session, [l.parent_id for l in lessons] + [l.tutor_id for l in lessons])
    issues = _latest_issues(session, [l.id for l in lessons])
    result = []
    for l in lessons:
        b = bookings[l.booking_id]
        issue = issues.get(l.id)
        result.append(view.model_validate(l, update={
            "subjects": b.subjects, "level": b.level, "mode": b.mode,
            "parent_name": names.get(l.parent_id), "tutor_name": names.get(l.tutor_id),
            "issue": _issue_read(issue) if issue else None,
            "recording_required": b.mode == LessonMode.online,
            "has_recording": l.recording_uploaded_at is not None and l.recording_deleted_at is None,
        }))
    return result


def _filtered(stmt, status_: LessonStatus | None, date_from: date | None, date_to: date | None):
    if status_:
        stmt = stmt.where(Lesson.status == status_)
    if date_from:
        stmt = stmt.where(Lesson.lesson_date >= date_from)
    if date_to:
        stmt = stmt.where(Lesson.lesson_date <= date_to)
    return stmt.order_by(Lesson.starts_at.desc())


def list_parent_lessons(session: Session, parent: User, status_, date_from, date_to) -> list[LessonParentView]:
    stmt = _filtered(select(Lesson).where(Lesson.parent_id == parent.id), status_, date_from, date_to)
    return _views(session, list(session.exec(stmt).all()), LessonParentView)


def list_tutor_lessons(session: Session, tutor: User, status_, date_from, date_to) -> list[LessonTutorView]:
    stmt = _filtered(select(Lesson).where(Lesson.tutor_id == tutor.id), status_, date_from, date_to)
    return _views(session, list(session.exec(stmt).all()), LessonTutorView)


def list_all_lessons(session: Session, status_, date_from, date_to, skip: int, limit: int) -> list[LessonAdminView]:
    stmt = _filtered(select(Lesson), status_, date_from, date_to).offset(skip).limit(limit)
    return _views(session, list(session.exec(stmt).all()), LessonAdminView)


def _get(session: Session, lesson_id: UUID) -> Lesson:
    lesson = session.exec(select(Lesson).where(Lesson.id == lesson_id).with_for_update()).first()
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    return lesson


# ---------- Tutor report ----------

def submit_report(session: Session, tutor: User, lesson_id: UUID, data: LessonReport,
                  now: datetime | None = None) -> LessonTutorView:
    now = now or clock.now()
    lesson = _get(session, lesson_id)
    if lesson.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only report your own lessons")
    if now < lesson.ends_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can report a lesson once it has ended")
    disputed_unreported = lesson.status == LessonStatus.disputed and lesson.reported_at is None
    if lesson.status != LessonStatus.confirmed and not disputed_unreported:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This lesson can't be reported (it is {lesson.status.value})")
    if lesson.status == LessonStatus.confirmed and now > lesson.ends_at + REPORT_WITHIN:
        raise HTTPException(status.HTTP_409_CONFLICT, "The 24-hour report deadline has passed")
    if session.get(Booking, lesson.booking_id).mode == LessonMode.online:
        # Checked again from the stored file, not only from what the upload claimed (spec 3 R2.1, R2.3).
        if lesson.recording_uploaded_at is None or _stored_recording_problem(lesson) is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "Upload the lesson recording before submitting your report")

    lesson.topic_covered = data.topic_covered
    lesson.homework = data.homework or None
    lesson.reported_at = now
    if lesson.status == LessonStatus.confirmed:
        lesson.status = LessonStatus.reported
        lesson.problem_window_ends_at = now + PROBLEM_WINDOW
    session.add(lesson)
    notifications.notify(
        session, lesson.parent_id, "Lesson report submitted",
        f"Your tutor reported the lesson on {notifications.date_text(lesson.lesson_date)}: {data.topic_covered}.\n"
        "If something wasn't right, you can report a problem within 24 hours.",
        "/dashboard/parent/lessons",
    )
    session.commit()
    return _views(session, [lesson], LessonTutorView)[0]


# ---------- Recordings (online lessons) ----------

def _stored_recording_problem(lesson: Lesson) -> str | None:
    """Why the stored file isn't an acceptable recording, or None if it is."""
    found = storage.head(lesson.recording_key) if lesson.recording_key else None
    if found is None:
        return "The recording upload didn't finish. Please upload it again."
    size, content_type = found
    if content_type.split(";")[0].strip() not in RECORDING_TYPES:
        return "The recording must be an MP4, WebM or MOV video."
    if size > MAX_RECORDING_BYTES or size == 0:
        return "The recording must be a video of at most 2 GB."
    return None


def request_recording_upload(session: Session, tutor: User, lesson_id: UUID, data: RecordingUploadIn,
                             now: datetime | None = None) -> RecordingUpload:
    """A short-lived link for the browser to upload the recording straight to storage (spec 3 R2.2)."""
    now = now or clock.now()
    lesson = _get(session, lesson_id)
    if lesson.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only upload recordings of your own lessons")
    if session.get(Booking, lesson.booking_id).mode != LessonMode.online:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Only online lessons have a recording")
    if lesson.reported_at is not None or lesson.status in (LessonStatus.refunded, LessonStatus.cancelled):
        raise HTTPException(status.HTTP_409_CONFLICT, "This lesson's recording can no longer be changed")
    if now < lesson.starts_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can upload the recording once the lesson has started")
    content_type = data.content_type.split(";")[0].strip().lower()
    extension = "." + data.filename.rsplit(".", 1)[-1].lower() if "." in data.filename else ""
    if content_type not in RECORDING_TYPES or extension not in RECORDING_TYPES.values():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The recording must be an MP4, WebM or MOV video")
    if data.size > MAX_RECORDING_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The recording must be at most 2 GB")

    old_key = lesson.recording_key
    lesson.recording_key = f"recordings/{lesson.id}/{uuid4().hex}{RECORDING_TYPES[content_type]}"
    lesson.recording_content_type = content_type
    lesson.recording_size = data.size
    lesson.recording_uploaded_at = None
    session.add(lesson)
    session.commit()
    if old_key:
        _delete_file(old_key)
    seconds = int(UPLOAD_LINK_TTL.total_seconds())
    return RecordingUpload(upload_url=storage.upload_url(lesson.recording_key, content_type, data.size, seconds),
                           content_type=content_type, expires_at=now + UPLOAD_LINK_TTL)


def complete_recording_upload(session: Session, tutor: User, lesson_id: UUID,
                              now: datetime | None = None) -> LessonTutorView:
    """The browser finished uploading: check the stored file's type and size (spec 3 R2.3)."""
    now = now or clock.now()
    lesson = _get(session, lesson_id)
    if lesson.tutor_id != tutor.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only upload recordings of your own lessons")
    if lesson.recording_key is None or lesson.reported_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "There's no recording upload waiting for this lesson")
    problem = _stored_recording_problem(lesson)
    if problem is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, problem)
    size, content_type = storage.head(lesson.recording_key)
    lesson.recording_size = size
    lesson.recording_content_type = content_type.split(";")[0].strip()
    lesson.recording_uploaded_at = now
    session.add(lesson)
    session.commit()
    return _views(session, [lesson], LessonTutorView)[0]


def recording_link(session: Session, user: User, lesson_id: UUID, now: datetime | None = None) -> RecordingLink:
    """A 15-minute viewing link for the lesson's parent, its tutor and admins only (spec 3 R2.4)."""
    now = now or clock.now()
    lesson = session.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lesson not found")
    if user.role != UserRole.admin and user.id not in (lesson.parent_id, lesson.tutor_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only watch recordings of your own lessons")
    if lesson.recording_uploaded_at is None or lesson.recording_deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This lesson has no recording")
    seconds = int(VIEW_LINK_TTL.total_seconds())
    return RecordingLink(url=storage.url(lesson.recording_key, seconds), expires_at=now + VIEW_LINK_TTL)


def _delete_file(key: str) -> bool:
    try:
        storage.delete(key)
        return True
    except Exception:
        logger.exception("Could not delete recording %s", key)
        return False


def delete_old_recordings(session: Session, now: datetime) -> int:
    """Deletes recordings 90 days after the lesson, unless a problem on that lesson is still open
    (spec 3 R2.6)."""
    open_issue = select(LessonIssue.id).where(LessonIssue.lesson_id == Lesson.id, LessonIssue.resolved_at.is_(None))
    rows = session.exec(select(Lesson).where(Lesson.recording_key.is_not(None),
                                             Lesson.recording_deleted_at.is_(None),
                                             Lesson.ends_at <= now - KEEP_RECORDINGS,
                                             ~open_issue.exists()).with_for_update()).all()
    deleted = 0
    for lesson in rows:
        if _delete_file(lesson.recording_key):
            lesson.recording_deleted_at = now
            session.add(lesson)
            deleted += 1
    session.commit()
    return deleted


# ---------- Problems ----------

def _notify_admins(session: Session, title: str, body: str) -> None:
    for admin_id in payments.admin_ids(session):
        notifications.notify(session, admin_id, title, body, "/admin/issues", email=False)


def report_problem(session: Session, parent: User, lesson_id: UUID, data: IssueCreate,
                   now: datetime | None = None) -> LessonParentView:
    now = now or clock.now()
    lesson = _get(session, lesson_id)
    if lesson.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only report problems with your own lessons")
    in_window = lesson.status == LessonStatus.reported and now < lesson.problem_window_ends_at
    unreported = lesson.status == LessonStatus.confirmed and now >= lesson.ends_at
    if lesson.status == LessonStatus.flagged:
        # The tutor didn't report; the automatic issue becomes the parent's.
        issue = session.exec(select(LessonIssue).where(LessonIssue.lesson_id == lesson.id,
                                                       LessonIssue.resolved_at.is_(None))).first()
        issue.raised_by = parent.id
        issue.kind = data.kind
        issue.description = data.description
    elif in_window or unreported:
        issue = LessonIssue(lesson_id=lesson.id, raised_by=parent.id, kind=data.kind, description=data.description)
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, "A problem can no longer be reported for this lesson")
    session.add(issue)
    lesson.status = LessonStatus.disputed
    lesson.earning_status = EarningStatus.on_hold
    session.add(lesson)
    notifications.notify(session, lesson.tutor_id, "A problem was reported",
                         f"The parent reported a problem with the lesson on "
                         f"{notifications.date_text(lesson.lesson_date)}. TutorLink will review it.",
                         "/dashboard/tutor/lessons")
    _notify_admins(session, "Lesson problem reported", f"Problem: {data.kind.value.replace('_', ' ')}.")
    session.commit()
    return _views(session, [lesson], LessonParentView)[0]


def list_issues(session: Session, open_only: bool) -> list[LessonAdminView]:
    has_issue = select(LessonIssue.id).where(LessonIssue.lesson_id == Lesson.id)
    if open_only:
        has_issue = has_issue.where(LessonIssue.resolved_at.is_(None))
    stmt = select(Lesson).where(has_issue.exists()).order_by(Lesson.updated_at.desc())
    return _views(session, list(session.exec(stmt).all()), LessonAdminView)


def resolve_issue(session: Session, admin: User, lesson_id: UUID, data: IssueResolve,
                  now: datetime | None = None) -> LessonAdminView:
    now = now or clock.now()
    lesson = _get(session, lesson_id)
    issue = session.exec(select(LessonIssue).where(LessonIssue.lesson_id == lesson.id,
                                                   LessonIssue.resolved_at.is_(None))).first()
    if issue is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This lesson has no open problem")

    when = notifications.date_text(lesson.lesson_date)
    if data.resolution == IssueResolution.refund:
        payments.lock_parent(session, lesson.parent_id)
        refund = Refund(parent_id=lesson.parent_id, booking_id=lesson.booking_id, reason=RefundReason.lesson_issue,
                        lesson_count=1, amount=lesson.price, status=RefundStatus.approved, note=data.note,
                        decided_by=admin.id, decided_at=now)
        session.add(refund)
        session.flush()
        payments.add_entry(session, lesson.parent_id, EntryKind.refund, lesson.price,
                           f"Refund for the lesson on {when}", refund_id=refund.id)
        lesson.status = LessonStatus.refunded
        lesson.earning_status = EarningStatus.void
        parent_text = (f"The lesson on {when} was refunded: {notifications.naira(lesson.price)} is now in your "
                       "TutorLink balance.")
        tutor_text = f"The lesson on {when} was refunded to the parent, so it won't be paid."
    elif data.resolution == IssueResolution.reschedule:
        starts_at = at_wat(data.new_date, data.new_start_time)
        if starts_at <= now:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The new lesson time must be in the future")
        lesson.lesson_date = data.new_date
        lesson.start_time = data.new_start_time
        lesson.end_time = data.new_end_time
        lesson.starts_at = starts_at
        lesson.ends_at = at_wat(data.new_date, data.new_end_time)
        lesson.status = LessonStatus.confirmed
        lesson.topic_covered = lesson.homework = None
        lesson.reported_at = lesson.problem_window_ends_at = None
        lesson.earning_status = EarningStatus.pending
        lesson.payout_due_at = lesson.ends_at + bookings_service.PAYOUT_AFTER
        new_when = f"{notifications.date_text(data.new_date)} at {data.new_start_time:%H:%M}"
        parent_text = tutor_text = f"The lesson from {when} has been rescheduled to {new_when}."
    else:
        first = _first_completions(session, [lesson])
        lesson.status = LessonStatus.completed
        lesson.earning_status = EarningStatus.payable
        lesson.payable_at = now
        for parent_id, tutor_id in first:
            _prompt_rating(session, parent_id, tutor_id)
        parent_text = f"After review, the lesson on {when} stands as taught."
        tutor_text = f"After review, the lesson on {when} stands, and it will be paid."

    issue.resolution = data.resolution
    issue.resolution_note = data.note
    issue.resolved_by = admin.id
    issue.resolved_at = now
    session.add(issue)
    session.add(lesson)
    note = f"\nNote from TutorLink: {data.note}" if data.note else ""
    notifications.notify(session, lesson.parent_id, "Problem resolved", parent_text + note, "/dashboard/parent/lessons")
    notifications.notify(session, lesson.tutor_id, "Problem resolved", tutor_text + note, "/dashboard/tutor/lessons")
    session.commit()
    if data.resolution == IssueResolution.refund:
        bookings_service.pay_due_periods(session, lesson.parent_id, now)
    session.refresh(lesson)
    return _views(session, [lesson], LessonAdminView)[0]


# ---------- Background jobs ----------

def _first_completions(session: Session, lessons: list[Lesson]) -> set[tuple]:
    """(parent, tutor) pairs among these lessons with no completed lesson yet and no rating:
    completing them now is their first completed lesson together. Call before marking them completed."""
    pairs = {(l.parent_id, l.tutor_id) for l in lessons}
    return {p for p in pairs if review_service.completed_lesson_count(session, *p) == 0
            and not review_service.has_reviewed(session, *p)}


def _prompt_rating(session: Session, parent_id: UUID, tutor_id: UUID) -> None:
    tutor_name = auth_service.full_names(session, [tutor_id]).get(tutor_id, "your tutor")
    notifications.notify(session, parent_id, f"How was your lesson with {tutor_name}?",
                         "Please take a moment to rate them. Your rating helps other parents choose the "
                         "best tutor.", f"/tutors/{tutor_id}")


def flag_unreported(session: Session, now: datetime) -> int:
    """No report 24 h after the lesson: possible absence, the earning is held for the admin (spec 1 R4.2)."""
    rows = session.exec(select(Lesson).where(Lesson.status == LessonStatus.confirmed,
                                             Lesson.ends_at <= now - REPORT_WITHIN).with_for_update()).all()
    for lesson in rows:
        lesson.status = LessonStatus.flagged
        lesson.earning_status = EarningStatus.on_hold
        session.add(lesson)
        session.add(LessonIssue(lesson_id=lesson.id, kind=IssueKind.no_report,
                                description="The tutor didn't submit a report within 24 hours."))
        notifications.notify(session, lesson.tutor_id, "Lesson report missing",
                             f"You didn't report the lesson on {notifications.date_text(lesson.lesson_date)} "
                             "within 24 hours. TutorLink will review it before it's paid.", "/dashboard/tutor/lessons")
        _notify_admins(session, "Lesson not reported", "A lesson wasn't reported within 24 hours.")
    session.commit()
    return len(rows)


def complete_reported(session: Session, now: datetime) -> int:
    """The parent's 24 h problem window closed with no problem: the tutor's earning becomes payable."""
    rows = session.exec(select(Lesson).where(Lesson.status == LessonStatus.reported,
                                             Lesson.problem_window_ends_at <= now).with_for_update()).all()
    first = _first_completions(session, list(rows))
    for lesson in rows:
        lesson.status = LessonStatus.completed
        lesson.earning_status = EarningStatus.payable
        lesson.payable_at = now
        session.add(lesson)
    for parent_id, tutor_id in first:
        _prompt_rating(session, parent_id, tutor_id)
    session.commit()
    return len(rows)
