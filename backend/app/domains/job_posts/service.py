"""Job posts (spec 2): parents post what they need and at what price, an admin reviews it, approved tutors
apply, and the parent chooses one, which creates a booking already taken (spec 1 R2.5 onward).

Functions that depend on the time take `now`, so tests can move the clock.
"""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core import clock
from app.core.clock import today_wat
from app.domains.auth import photos
from app.domains.auth import service as auth_service
from app.domains.auth.models import User
from app.domains.bookings import schedule
from app.domains.bookings import service as bookings
from app.domains.bookings.models import RECORDING_CONSENT, BookingParentView, LessonMode
from app.domains.fees import service as fees_service
from app.domains.job_posts.models import (
    ApplicantView,
    ApplicationIn,
    ApplicationStatus,
    ApplicationTutorView,
    JobAdminView,
    JobApplication,
    JobIn,
    JobParentView,
    JobPost,
    JobReviewIn,
    JobSlot,
    JobStatus,
    JobTutorView,
)
from app.domains.notifications import service as notifications
from app.domains.reviews import service as reviews
from app.domains.tutors import service as tutor_service
from app.domains.tutors.models import EducationLevel, WeeklyTime

CLASH_REASON = "The job's new lesson times clash with your other bookings."
# A parent can edit or close a job until a tutor is chosen (R1.3).
EDITABLE = (JobStatus.pending, JobStatus.rejected, JobStatus.open)


# ---------- Reading ----------

def _slots(session: Session, job_ids: list[UUID]) -> dict[UUID, list[WeeklyTime]]:
    grouped: dict[UUID, list[WeeklyTime]] = {jid: [] for jid in job_ids}
    if job_ids:
        for slot in session.exec(select(JobSlot).where(JobSlot.job_id.in_(job_ids))
                                 .order_by(JobSlot.day_of_week, JobSlot.start_time)).all():
            grouped[slot.job_id].append(WeeklyTime.model_validate(slot))
    return grouped


def _parent_views(session: Session, jobs: list[JobPost]) -> list[JobParentView]:
    ids = [j.id for j in jobs]
    slots = _slots(session, ids)
    counts = dict(session.exec(
        select(JobApplication.job_id, func.count()).where(JobApplication.job_id.in_(ids),
                                                          JobApplication.status != ApplicationStatus.withdrawn)
        .group_by(JobApplication.job_id)
    ).all()) if ids else {}
    parent_rate = fees_service.current(session).parent_fee_rate
    return [JobParentView.model_validate(j, update={
        "slots": slots[j.id], "applicant_count": counts.get(j.id, 0),
        "parent_price_per_lesson": fees_service.parent_price(j.price, parent_rate),
    }) for j in jobs]


def _tutor_views(session: Session, tutor: User, jobs: list[JobPost]) -> list[JobTutorView]:
    ids = [j.id for j in jobs]
    slots = _slots(session, ids)
    parents = [j.parent_id for j in jobs]
    names = auth_service.full_names(session, parents)
    pictures = photos.urls_for(session, parents)
    mine = {a.job_id: a for a in session.exec(
        select(JobApplication).where(JobApplication.tutor_id == tutor.id, JobApplication.job_id.in_(ids))
    ).all()} if ids else {}
    tutor_rate = fees_service.current(session).tutor_fee_rate
    return [JobTutorView.model_validate(j, update={
        "slots": slots[j.id],
        "tutor_fee_rate": tutor_rate, "tutor_earning_per_lesson": fees_service.tutor_earning(j.price, tutor_rate),
        # First name only: tutors never see the parent's surname or contact details (R2.4).
        "parent_first_name": (names.get(j.parent_id) or "Parent").split()[0],
        "parent_photo_url": pictures.get(j.parent_id),
        "my_application": ApplicationTutorView.model_validate(mine[j.id]) if j.id in mine else None,
    }) for j in jobs]


def _get(session: Session, job_id: UUID, *, lock: bool = False) -> JobPost:
    stmt = select(JobPost).where(JobPost.id == job_id)
    if lock:
        stmt = stmt.with_for_update()
    job = session.exec(stmt).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


def _own(session: Session, parent: User, job_id: UUID, *, lock: bool = False) -> JobPost:
    job = _get(session, job_id, lock=lock)
    if job.parent_id != parent.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only manage your own jobs")
    return job


def _require_approved(session: Session, tutor: User) -> None:
    """Only approved tutors can browse and apply (R2.1)."""
    if tutor_service.get_approved_profile(session, tutor.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Jobs are open to approved tutors only")


def list_parent_jobs(session: Session, parent: User) -> list[JobParentView]:
    rows = session.exec(select(JobPost).where(JobPost.parent_id == parent.id).order_by(JobPost.created_at.desc()))
    return _parent_views(session, list(rows.all()))


def get_job(session: Session, user: User, job_id: UUID) -> JobParentView | JobTutorView:
    job = _get(session, job_id)
    if user.id == job.parent_id:
        return _parent_views(session, [job])[0]
    if user.role.value == "tutor":
        _require_approved(session, user)
        applied = session.exec(select(JobApplication.id).where(JobApplication.job_id == job.id,
                                                               JobApplication.tutor_id == user.id)).first()
        if job.status == JobStatus.open or applied is not None:
            return _tutor_views(session, user, [job])[0]
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own jobs")


def browse(session: Session, tutor: User, *, subject: str | None, level: EducationLevel | None,
           mode: LessonMode | None, area: str | None, skip: int, limit: int) -> list[JobTutorView]:
    """Open jobs, newest first. A job matches a subject if any of its subjects is that one (R2.2)."""
    _require_approved(session, tutor)
    stmt = select(JobPost).where(JobPost.status == JobStatus.open)
    if subject:
        listed = func.unnest(JobPost.subjects).table_valued("subject").render_derived()
        stmt = stmt.where(select(listed.c.subject)
                          .where(func.lower(listed.c.subject) == subject.strip().lower()).exists())
    if level:
        stmt = stmt.where(JobPost.level == level)
    if mode:
        stmt = stmt.where(JobPost.mode == mode)
    if area:
        stmt = stmt.where(JobPost.area.ilike(f"%{area.strip()}%"))
    rows = session.exec(stmt.order_by(JobPost.created_at.desc()).offset(skip).limit(limit)).all()
    return _tutor_views(session, tutor, list(rows))


def my_applications(session: Session, tutor: User) -> list[JobTutorView]:
    """Every job the tutor applied to, whatever its status, newest application first."""
    rows = session.exec(select(JobPost).join(JobApplication, JobApplication.job_id == JobPost.id)
                        .where(JobApplication.tutor_id == tutor.id)
                        .order_by(JobApplication.created_at.desc())).all()
    return _tutor_views(session, tutor, list(rows))


# ---------- Posting and editing (parent) ----------

def _check_times(data: JobIn, now: datetime) -> None:
    for i, slot in enumerate(data.slots):
        if any(schedule.overlaps(slot, other) for other in data.slots[i + 1:]):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Two of the lesson times overlap")
    if data.start_date < today_wat(now):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start_date can't be in the past")
    if schedule.plan_period(data.slots, data.billing_period, data.start_date, data.end_date) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "There are no lessons between these dates")


def _write(session: Session, job: JobPost, data: JobIn, now: datetime) -> None:
    for field, value in data.model_dump(exclude={"slots", "recording_consent"}).items():
        setattr(job, field, value)
    consent_at = bookings.check_recording_consent(data.mode, data.recording_consent, now)
    job.recording_consent_at = consent_at
    job.recording_consent_text = RECORDING_CONSENT if consent_at else None
    if job.mode == LessonMode.online:
        job.area = data.area or None
    session.add(job)
    session.flush()
    for old in session.exec(select(JobSlot).where(JobSlot.job_id == job.id)).all():
        session.delete(old)
    session.add_all(JobSlot(job_id=job.id, **slot.model_dump()) for slot in data.slots)


def post_job(session: Session, parent: User, data: JobIn, now: datetime | None = None) -> JobParentView:
    """The job waits for an admin's review before tutors can see it (R1.4)."""
    now = now or clock.now()
    if parent.photo_key is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add a profile picture before posting a job")
    _check_times(data, now)
    job = JobPost(parent_id=parent.id, **data.model_dump(exclude={"slots", "recording_consent"}),
                  created_at=now, updated_at=now)
    _write(session, job, data, now)
    session.commit()
    session.refresh(job)
    return _parent_views(session, [job])[0]


def update_job(session: Session, parent: User, job_id: UUID, data: JobIn,
               now: datetime | None = None) -> JobParentView:
    """Replaces the details of a job no tutor has been chosen for. The edited job goes back for review, so
    tutors see it again only once an admin approves it (R1.4). Applicants are told; those whose bookings now
    clash with the new times are withdrawn and told why (R1.3)."""
    now = now or clock.now()
    job = _own(session, parent, job_id, lock=True)
    if job.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A {job.status.value} job can't be edited")
    _check_times(data, now)
    _write(session, job, data, now)
    job.status = JobStatus.pending
    job.review_note = None
    job.reviewed_at = None
    job.updated_at = now
    for application in session.exec(select(JobApplication).where(
            JobApplication.job_id == job.id, JobApplication.status == ApplicationStatus.applied)).all():
        taken = bookings.taken_slots(session, application.tutor_id)
        if any(schedule.overlaps(slot, other) for slot in data.slots for other in taken):
            application.status = ApplicationStatus.withdrawn
            application.withdrawn_reason = CLASH_REASON
            session.add(application)
            notifications.notify(session, application.tutor_id, "Application withdrawn",
                                 f"A job you applied to changed its lesson times. {CLASH_REASON}",
                                 "/dashboard/tutor/jobs")
        else:
            notifications.notify(session, application.tutor_id, "A job you applied to changed",
                                 f"The parent updated their job for {', '.join(job.subjects)}. "
                                 "Please check the new details. TutorLink reviews the changes before the job "
                                 "is open again.", f"/dashboard/tutor/jobs/{job.id}")
    session.commit()
    session.refresh(job)
    return _parent_views(session, [job])[0]


def close_job(session: Session, parent: User, job_id: UUID, now: datetime | None = None) -> JobParentView:
    now = now or clock.now()
    job = _own(session, parent, job_id, lock=True)
    if job.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "A job can only be closed before a tutor is chosen")
    job.status = JobStatus.closed
    job.closed_at = now
    session.add(job)
    session.commit()
    session.refresh(job)
    return _parent_views(session, [job])[0]


# ---------- Applying (tutor) ----------

def apply(session: Session, tutor: User, job_id: UUID, data: ApplicationIn) -> JobTutorView:
    _require_approved(session, tutor)
    job = _get(session, job_id, lock=True)
    if job.status != JobStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "This job is no longer open")
    existing = session.exec(select(JobApplication.id).where(JobApplication.job_id == job.id,
                                                            JobApplication.tutor_id == tutor.id)).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already applied to this job")
    slots = _slots(session, [job.id])[job.id]
    taken = bookings.taken_slots(session, tutor.id)
    if any(schedule.overlaps(slot, other) for slot in slots for other in taken):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have lessons at one of this job's times")
    session.add(JobApplication(job_id=job.id, tutor_id=tutor.id, note=data.note or None))
    notifications.notify(session, job.parent_id, "New applicant",
                         f"A tutor applied to your job for {', '.join(job.subjects)}.",
                         f"/dashboard/parent/jobs/{job.id}")
    try:
        session.commit()
    except IntegrityError:  # applied twice at the same moment
        session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already applied to this job")
    return _tutor_views(session, tutor, [job])[0]


def withdraw(session: Session, tutor: User, job_id: UUID) -> JobTutorView:
    job = _get(session, job_id, lock=True)
    application = session.exec(select(JobApplication).where(JobApplication.job_id == job.id,
                                                            JobApplication.tutor_id == tutor.id)).first()
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You haven't applied to this job")
    # Pending: an edited job back for review still has its applications.
    if job.status not in (JobStatus.open, JobStatus.pending) or application.status != ApplicationStatus.applied:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can only withdraw from an open job")
    application.status = ApplicationStatus.withdrawn
    session.add(application)
    session.commit()
    return _tutor_views(session, tutor, [job])[0]


# ---------- Choosing a tutor (parent) ----------

def list_applicants(session: Session, parent: User, job_id: UUID) -> list[ApplicantView]:
    job = _own(session, parent, job_id)
    rows = list(session.exec(select(JobApplication).where(JobApplication.job_id == job.id,
                                                          JobApplication.status != ApplicationStatus.withdrawn)
                             .order_by(JobApplication.created_at)).all())
    tutors = [a.tutor_id for a in rows]
    names = auth_service.full_names(session, tutors)
    pictures = photos.urls_for(session, tutors)
    ratings = reviews.rating_stats(session, tutors)
    return [ApplicantView.model_validate(a, update={
        "tutor_name": names.get(a.tutor_id), "tutor_photo_url": pictures.get(a.tutor_id),
        "average_rating": ratings.get(a.tutor_id, (None, 0))[0],
        "rating_count": ratings.get(a.tutor_id, (None, 0))[1],
    }) for a in rows]


def choose(session: Session, parent: User, job_id: UUID, application_id: UUID,
           now: datetime | None = None) -> BookingParentView:
    """Accepting an applicant books them from the job: the booking is taken at once, awaiting payment,
    and the job becomes ongoing (R3.2, R3.3)."""
    now = now or clock.now()
    job = _own(session, parent, job_id, lock=True)
    if job.status == JobStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Your job is waiting for review. You can choose a tutor once it's approved.")
    if job.status != JobStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "This job is no longer open")
    application = session.exec(select(JobApplication).where(JobApplication.id == application_id,
                                                            JobApplication.job_id == job.id)
                               .with_for_update()).first()
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if application.status != ApplicationStatus.applied:
        raise HTTPException(status.HTTP_409_CONFLICT, "This tutor has withdrawn their application")
    if tutor_service.get_approved_profile(session, application.tutor_id) is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This tutor can't take jobs right now")

    others = session.exec(select(JobApplication.tutor_id).where(
        JobApplication.job_id == job.id, JobApplication.status == ApplicationStatus.applied,
        JobApplication.id != application.id)).all()

    def link(booking) -> None:
        """Runs once the booking row exists, so the job and booking commit together."""
        job.status = JobStatus.ongoing
        job.booking_id = booking.id
        application.status = ApplicationStatus.chosen
        session.add(job)
        session.add(application)
        notifications.notify(session, application.tutor_id, "You've been chosen",
                             f"A parent chose you for their job: {', '.join(job.subjects)}. The lessons start "
                             "once they pay for the first ones.", "/dashboard/tutor/bookings")
        for tutor_id in others:
            notifications.notify(session, tutor_id, "Job taken",
                                 f"The job for {', '.join(job.subjects)} you applied to went to another tutor.",
                                 "/dashboard/tutor/jobs")

    booking = bookings.book_from_job(
        session, parent_id=parent.id, tutor_id=application.tutor_id, job_id=job.id, subjects=job.subjects,
        level=job.level, mode=job.mode, billing_period=job.billing_period, start_date=job.start_date,
        end_date=job.end_date, price=job.price, child_strengths=job.child_strengths,
        child_weaknesses=job.child_weaknesses, slots=_slots(session, [job.id])[job.id], now=now,
        recording_consent_at=job.recording_consent_at, on_created=link,
    )
    return bookings.parent_view(session, booking)


# ---------- Review (admin) ----------

def _admin_views(session: Session, jobs: list[JobPost]) -> list[JobAdminView]:
    slots = _slots(session, [j.id for j in jobs])
    names = auth_service.full_names(session, [j.parent_id for j in jobs])
    return [JobAdminView.model_validate(j, update={"slots": slots[j.id], "parent_name": names.get(j.parent_id)})
            for j in jobs]


def admin_list(session: Session, status_filter: JobStatus | None) -> list[JobAdminView]:
    """Oldest change first, so the review queue (`pending`) is handled in order."""
    stmt = select(JobPost)
    if status_filter is not None:
        stmt = stmt.where(JobPost.status == status_filter)
    return _admin_views(session, list(session.exec(stmt.order_by(JobPost.updated_at)).all()))


def review(session: Session, job_id: UUID, data: JobReviewIn, now: datetime | None = None) -> JobAdminView:
    """Approving opens the job to tutors; rejecting tells the parent why, and they can edit it to resubmit
    (R1.4)."""
    now = now or clock.now()
    job = _get(session, job_id, lock=True)
    if job.status != JobStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "This job isn't waiting for review")
    job.status = data.status
    job.review_note = data.note if data.status == JobStatus.rejected else None
    job.reviewed_at = now
    session.add(job)
    subjects = ", ".join(job.subjects)
    if data.status == JobStatus.open:
        notifications.notify(session, job.parent_id, "Your job is live",
                             f"TutorLink approved your job for {subjects}. Tutors can now see it and apply.",
                             f"/dashboard/parent/jobs/{job.id}")
    else:
        notifications.notify(session, job.parent_id, "Your job wasn't approved",
                             f"TutorLink couldn't approve your job for {subjects}.\nReason: {data.note}\n"
                             "You can edit the job and it will be reviewed again.",
                             f"/dashboard/parent/jobs/{job.id}")
    session.commit()
    session.refresh(job)
    return _admin_views(session, [job])[0]
