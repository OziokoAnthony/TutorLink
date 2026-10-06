from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from starlette.concurrency import run_in_threadpool

from app.db.session import get_session
from app.domains.webhooks import service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payment")
async def payment_webhook(request: Request, session: Session = Depends(get_session)):
    raw_body = await request.body()  # raw bytes, before any JSON parsing
    return await run_in_threadpool(
        service.process_payment_webhook,
        session,
        raw_body,
        request.headers.get("x-paystack-signature"),
        request.headers.get("x-paystack-event-id"),
    )
