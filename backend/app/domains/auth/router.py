from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth import photos, service
from app.domains.auth.models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    GoogleRegisterRequest,
    GoogleRegisterResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    User,
    UserRole,
)
from app.domains.notifications import service as notifications

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles([UserRole.admin])


@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    return service.register(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    return service.login(session, data)


@router.post("/google/register", response_model=GoogleRegisterResponse, status_code=status.HTTP_201_CREATED)
def google_register(data: GoogleRegisterRequest, session: Session = Depends(get_session)):
    """Tutors register only here (spec 4 R1.1); parents may too. Tutors get `password`, shown once;
    parents get `access_token`."""
    return service.google_register(session, data)


@router.post("/google/login", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, session: Session = Depends(get_session)):
    """Parents only. 404 when no account has this Google email: the frontend then offers sign-up."""
    return service.google_login(session, data)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks,
                    session: Session = Depends(get_session)):
    """Always the same answer, and the email goes out after responding, so the form doesn't reveal
    who has an account (spec 4 R0.7)."""
    email = service.forgot_password(session, data)
    if email:
        background_tasks.add_task(notifications.send_email, *email)
    return {"detail": "If an account uses this email, we've sent it a link to set a new password."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(data: ResetPasswordRequest, session: Session = Depends(get_session)):
    service.reset_password(session, data)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return service.build_me(session, user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePasswordRequest, user: User = Depends(get_current_user),
                    session: Session = Depends(get_session)):
    """Tutors use this to replace the password emailed to them at registration."""
    service.change_password(session, user, data)


@router.put("/me/photo", response_model=MeResponse)
def upload_photo(file: UploadFile = File(...), user: User = Depends(get_current_user),
                 session: Session = Depends(get_session)):
    """Sets the profile picture: JPG, PNG or WebP up to 5 MB, stored as a 512x512 square."""
    data = photos.read_upload(file)
    photos.set_photo(session, user, data)
    return service.build_me(session, user)


@admin_router.delete("/users/{user_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def remove_photo(user_id: UUID, admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    """Removes an inappropriate profile picture; the user is asked to upload a new one."""
    service.remove_photo(session, user_id)
