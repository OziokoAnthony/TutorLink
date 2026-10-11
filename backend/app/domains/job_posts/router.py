from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.bookings.models import BookingParentView, LessonMode
from app.domains.job_posts import service
from app.domains.job_posts.models import (
    ApplicantView,
    ApplicationIn,
    JobAdminView,
    JobIn,
    JobParentView,
    JobReviewIn,
    JobStatus,
    JobTutorView,
)
from app.domains.tutors.models import EducationLevel

router = APIRouter(prefix="/jobs", tags=["jobs"])
admin_router = APIRouter(prefix="/admin/jobs", tags=["admin"])

parent_only = require_roles([UserRole.parent])
tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


@router.post("", response_model=JobParentView, status_code=status.HTTP_201_CREATED)
def post_job(data: JobIn, parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.post_job(session, parent, data)


@router.get("", response_model=list[JobTutorView])
def browse(subject: str | None = None, level: EducationLevel | None = None, mode: LessonMode | None = None,
           area: str | None = None, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100),
           tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """Open jobs, for approved tutors only (spec 2 R2.1, R2.2)."""
    return service.browse(session, tutor, subject=subject, level=level, mode=mode, area=area, skip=skip, limit=limit)


@router.get("/me", response_model=list[JobParentView])
def my_jobs(parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.list_parent_jobs(session, parent)


@router.get("/applications/me", response_model=list[JobTutorView])
def my_applications(tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.my_applications(session, tutor)


@router.get("/{job_id}", response_model=JobParentView | JobTutorView)
def get_job(job_id: UUID, user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return service.get_job(session, user, job_id)


@router.put("/{job_id}", response_model=JobParentView)
def update_job(job_id: UUID, data: JobIn, parent: User = Depends(parent_only),
               session: Session = Depends(get_session)):
    return service.update_job(session, parent, job_id, data)


@router.post("/{job_id}/close", response_model=JobParentView)
def close_job(job_id: UUID, parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.close_job(session, parent, job_id)


@router.post("/{job_id}/apply", response_model=JobTutorView, status_code=status.HTTP_201_CREATED)
def apply(job_id: UUID, data: ApplicationIn, tutor: User = Depends(tutor_only),
          session: Session = Depends(get_session)):
    return service.apply(session, tutor, job_id, data)


@router.post("/{job_id}/withdraw", response_model=JobTutorView)
def withdraw(job_id: UUID, tutor: User = Depends(tutor_only), session: Session = Depends(get_session)):
    return service.withdraw(session, tutor, job_id)


@router.get("/{job_id}/applications", response_model=list[ApplicantView])
def applicants(job_id: UUID, parent: User = Depends(parent_only), session: Session = Depends(get_session)):
    return service.list_applicants(session, parent, job_id)


@router.post("/{job_id}/applications/{application_id}/choose", response_model=BookingParentView,
             status_code=status.HTTP_201_CREATED)
def choose(job_id: UUID, application_id: UUID, parent: User = Depends(parent_only),
           session: Session = Depends(get_session)):
    """Books the applicant from the job: taken at once, awaiting payment (spec 2 R3.2)."""
    return service.choose(session, parent, job_id, application_id)


@admin_router.get("", response_model=list[JobAdminView])
def admin_jobs(status_filter: JobStatus | None = Query(None, alias="status"),
               admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Oldest change first. `?status=pending` is the review queue (spec 2 R1.4)."""
    return service.admin_list(session, status_filter)


@admin_router.patch("/{job_id}", response_model=JobAdminView)
def review_job(job_id: UUID, data: JobReviewIn, admin: User = Depends(admin_only),
               session: Session = Depends(get_session)):
    """Approve (`open`) or reject with a note the parent sees (spec 2 R1.4)."""
    return service.review(session, job_id, data)
