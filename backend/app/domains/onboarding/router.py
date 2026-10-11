"""Tutor onboarding (spec 4 R2) and NIN verification (R3)."""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlmodel import Session

from app.core.deps import require_roles
from app.db.session import get_session
from app.domains.auth import photos
from app.domains.auth.models import User, UserRole
from app.domains.onboarding import service
from app.domains.onboarding.models import NinResult, Onboarding

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

tutor_only = require_roles([UserRole.tutor])


@router.get("", response_model=Onboarding)
def my_onboarding(user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """The tutor's checklist: Profile, NIN, waiting for review (R2.1)."""
    return service.get_onboarding(session, user)


@router.post("/nin", response_model=NinResult)
def verify_nin(nin: str = Form(..., pattern=r"^\d{11}$"), selfie: UploadFile = File(...),
               user: User = Depends(tutor_only), session: Session = Depends(get_session)):
    """Checks the 11-digit NIN and a selfie taken in the browser with Dojah (R3.2-R3.4). A failed check
    is a 200 that says which check failed; at most 3 attempts per 24 hours (R3.8)."""
    return service.verify_nin(session, user, nin, photos.read_upload(selfie, "Selfies"))
