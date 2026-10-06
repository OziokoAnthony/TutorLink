from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from app.db.session import get_session
from app.domains.auth.router import router as auth_router
from app.domains.billing.router import router as billing_router
from app.domains.reviews.router import router as reviews_router
from app.domains.schedules.router import router as schedules_router
from app.domains.schedules.router import tutor_router as tutor_schedule_router
from app.domains.sessions.router import admin_router as admin_sessions_router
from app.domains.sessions.router import router as sessions_router
from app.domains.tutors.router import admin_router as admin_tutors_router
from app.domains.tutors.router import router as tutors_router
from app.domains.webhooks.router import router as webhooks_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(tutors_router)
api_router.include_router(tutor_schedule_router)
api_router.include_router(reviews_router)
api_router.include_router(admin_tutors_router)
api_router.include_router(schedules_router)
api_router.include_router(sessions_router)
api_router.include_router(admin_sessions_router)
api_router.include_router(billing_router)
api_router.include_router(webhooks_router)


@api_router.get("/health", tags=["system"])
def health(session: Session = Depends(get_session)):
    try:
        session.exec(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "error", "db": "disconnected"})
    return {"status": "ok", "db": "connected"}
