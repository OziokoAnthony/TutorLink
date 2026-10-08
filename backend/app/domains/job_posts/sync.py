"""Keeps a job in step with the booking made from it. Called by the bookings service whenever a booking
closes, inside its transaction. It imports only models, so the bookings service can import it."""

from sqlmodel import Session, select

from app.domains.bookings.models import Booking, BookingPeriod, PeriodStatus
from app.domains.job_posts.models import ApplicationStatus, JobApplication, JobPost, JobStatus
from app.domains.notifications import service as notifications


def booking_closed(session: Session, booking: Booking) -> None:
    """A booking that never got paid (released, or ended or cancelled before paying) puts its job back
    to open, and the chosen tutor's application stays as an application (spec 2 R3.4). A booking that
    was paid and has now closed completes its job (R1.2, R3.5)."""
    if booking.job_id is None:
        return
    job = session.exec(select(JobPost).where(JobPost.id == booking.job_id).with_for_update()).first()
    if job is None or job.booking_id != booking.id or job.status != JobStatus.ongoing:
        return
    paid = session.exec(select(BookingPeriod.id).where(BookingPeriod.booking_id == booking.id,
                                                       BookingPeriod.status == PeriodStatus.paid)).first()
    if paid is None:
        job.status = JobStatus.open
        job.booking_id = None
        chosen = session.exec(select(JobApplication).where(JobApplication.job_id == job.id,
                                                           JobApplication.tutor_id == booking.tutor_id)).first()
        if chosen is not None and chosen.status == ApplicationStatus.chosen:
            chosen.status = ApplicationStatus.applied
            session.add(chosen)
        notifications.notify(session, job.parent_id, "Your job is open again",
                             "The booking from your job closed before it was paid, so tutors can see your job "
                             "again. You can choose another applicant.", f"/dashboard/parent/jobs/{job.id}")
    else:
        job.status = JobStatus.completed
        notifications.notify(session, job.parent_id, "Job completed",
                             f"The booking from your job for {', '.join(job.subjects)} has ended.",
                             f"/dashboard/parent/jobs/{job.id}")
    session.add(job)
