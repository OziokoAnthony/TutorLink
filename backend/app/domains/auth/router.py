from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, Response, UploadFile, status
from sqlmodel import Session

from app.core.deps import clear_session_cookie, get_current_user, require_roles, set_session_cookie
from app.db.session import get_session
from app.domains.auth import limits, photos, service
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
def register(data: RegisterRequest, request: Request, session: Session = Depends(get_session)):
    limits.hit(session, limits.SIGNUP_IP, limits.client_ip(request))
    return service.register(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    """Sets the httpOnly login cookie; the token is also in the body for API clients."""
    result = service.login(session, data, limits.client_ip(request))
    set_session_cookie(response, result.access_token, result.role.value)
    return result


@router.post("/google/register", response_model=GoogleRegisterResponse, status_code=status.HTTP_201_CREATED)
def google_register(data: GoogleRegisterRequest, request: Request, response: Response,
                    session: Session = Depends(get_session)):
    """Parents and tutors (spec 4 R1.1): signed in at once (login cookie, and `access_token`)."""
    limits.hit(session, limits.SIGNUP_IP, limits.client_ip(request))
    result = service.google_register(session, data)
    set_session_cookie(response, result.access_token, result.user.role.value)
    return result


@router.post("/google/login", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, request: Request, response: Response,
                 session: Session = Depends(get_session)):
    """Parents and tutors. 404 when no account has this Google email: the frontend then offers sign-up."""
    limits.hit(session, limits.GOOGLE_IP, limits.client_ip(request))
    result = service.google_login(session, data)
    set_session_cookie(response, result.access_token, result.role.value)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """Removes this browser's login cookie."""
    clear_session_cookie(response)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(data: ForgotPasswordRequest, request: Request, background_tasks: BackgroundTasks,
                    session: Session = Depends(get_session)):
    """Always the same answer, and the email goes out after responding, so the form doesn't reveal
    who has an account (spec 4 R0.7). Limited per email and per IP whether or not the account exists."""
    limits.check(session, limits.RESET_IP, limits.client_ip(request))
    limits.hit(session, limits.RESET_EMAIL, data.email)
    limits.hit(session, limits.RESET_IP, limits.client_ip(request))
    email = service.forgot_password(session, data)
    if email:
        background_tasks.add_task(notifications.send_email, *email)
    return {"detail": "If an account uses this email, we've sent it a link to set a new password."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(data: ResetPasswordRequest, request: Request, session: Session = Depends(get_session)):
    limits.hit(session, limits.RESET_USE_IP, limits.client_ip(request))
    service.reset_password(session, data)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return service.build_me(session, user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: ChangePasswordRequest, response: Response, user: User = Depends(get_current_user),
                    session: Session = Depends(get_session)):
    """Change a password while logged in, knowing the current one. Every other device is logged out; this
    browser gets a new login cookie."""
    token = service.change_password(session, user, data)
    set_session_cookie(response, token, user.role.value)


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
