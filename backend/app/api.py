from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.db.session import get_session
from app.domains.auth.router import admin_router as admin_users_router
from app.domains.auth.router import router as auth_router
from app.domains.bookings.router import admin_router as admin_bookings_router
from app.domains.bookings.router import router as bookings_router
from app.domains.bookings.router import tutor_router as tutor_schedule_router
from app.domains.certificates.router import admin_router as admin_certificates_router
from app.domains.certificates.router import router as certificates_router
from app.domains.exam.router import admin_router as admin_exam_router
from app.domains.exam.router import router as exam_router
from app.domains.fees.router import router as fees_router
from app.domains.files.router import router as files_router
from app.domains.job_posts.router import router as jobs_router
from app.domains.lessons.router import admin_router as admin_lessons_router
from app.domains.lessons.router import router as lessons_router
from app.domains.notifications.router import router as notifications_router
from app.domains.onboarding.router import router as onboarding_router
from app.domains.payments.router import admin_router as admin_withdrawals_router
from app.domains.payments.router import banks_router
from app.domains.payments.router import router as wallet_router
from app.domains.payouts.router import admin_router as admin_payouts_router
from app.domains.payouts.router import router as earnings_router
from app.domains.reviews.router import router as reviews_router
from app.domains.tutors.router import admin_router as admin_tutors_router
from app.domains.tutors.router import router as tutors_router
from app.domains.webhooks.router import router as webhooks_router

api_router = APIRouter()

for router in (
    auth_router, admin_users_router,
    tutors_router, tutor_schedule_router, reviews_router, admin_tutors_router,
    onboarding_router, certificates_router, admin_certificates_router, exam_router, admin_exam_router,
    bookings_router, admin_bookings_router, jobs_router,
    lessons_router, admin_lessons_router,
    wallet_router, banks_router, admin_withdrawals_router,
    earnings_router, admin_payouts_router,
    fees_router, notifications_router, files_router, webhooks_router,
):
    api_router.include_router(router)


@api_router.get("/health", tags=["system"])
def health(session: Session = Depends(get_session)):
    try:
        session.exec(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "db": "disconnected"})
    return {"status": "ok", "db": "connected"}
