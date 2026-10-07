import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router, health
from app.core.config import settings
from app.jobs import start_scheduler

# Route our own `app.*` loggers (emails, Paystack, webhooks) to stdout alongside uvicorn's.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = start_scheduler() if settings.RUN_SCHEDULER else None
    yield
    if stop is not None:
        stop.set()


app = FastAPI(title="TutorLink API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(api_router, prefix="/v1")
# Unversioned alias for load balancers / container healthchecks (CLAUDE.md lists GET /health).
app.add_api_route("/health", health, methods=["GET"], tags=["system"])
