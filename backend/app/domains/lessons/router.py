from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.lessons import service
from app.domains.lessons.models import (
    IssueCreate,
    IssueResolve,
    LessonAdminView,
    LessonParentView,
    LessonReport,
    LessonStatus,
    LessonTutorView,
)

router = APIRouter(prefix="/lessons", tags=["lessons"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

parent_only = require_roles([UserRole.parent])
tutor_only = require_roles([UserRole.tutor])
admin_only = require_roles([UserRole.admin])


class LessonFilters:
    def __init__(self, status: LessonStatus | None = None, date_from: date | None = None, date_to: date | None = None):
        self.status = status
        self.date_from = date_from
        self.date_to = date_to


@router.get("/me", response_model=list[LessonParentView])
def my_lessons(filters: LessonFilters = Depends(), parent: User = Depends(parent_only),
               session: Session = Depends(get_session)):
    return service.list_parent_lessons(session, parent, filters.status, filters.date_from, filters.date_to)


@router.get("/tutor/me", response_model=list[LessonTutorView])
def my_tutor_lessons(filters: LessonFilters = Depends(), tutor: User = Depends(tutor_only),
                     session: Session = Depends(get_session)):
    return service.list_tutor_lessons(session, tutor, filters.status, filters.date_from, filters.date_to)


@router.post("/{lesson_id}/report", response_model=LessonTutorView)
def submit_report(lesson_id: UUID, data: LessonReport, tutor: User = Depends(tutor_only),
                  session: Session = Depends(get_session)):
    return service.submit_report(session, tutor, lesson_id, data)


@router.post("/{lesson_id}/problem", response_model=LessonParentView)
def report_problem(lesson_id: UUID, data: IssueCreate, parent: User = Depends(parent_only),
                   session: Session = Depends(get_session)):
    return service.report_problem(session, parent, lesson_id, data)


@admin_router.get("/lessons", response_model=list[LessonAdminView])
def all_lessons(filters: LessonFilters = Depends(), skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.list_all_lessons(session, filters.status, filters.date_from, filters.date_to, skip, limit)


@admin_router.get("/issues", response_model=list[LessonAdminView])
def issues(open_only: bool = True, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    return service.list_issues(session, open_only)


@admin_router.post("/lessons/{lesson_id}/resolve", response_model=LessonAdminView)
def resolve(lesson_id: UUID, data: IssueResolve, admin: User = Depends(admin_only),
            session: Session = Depends(get_session)):
    return service.resolve_issue(session, admin, lesson_id, data)
