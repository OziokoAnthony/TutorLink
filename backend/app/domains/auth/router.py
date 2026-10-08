from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlmodel import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_session
from app.domains.auth import photos, service
from app.domains.auth.models import ChangePasswordRequest, LoginRequest, MeResponse, RegisterRequest, TokenResponse, User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_roles([UserRole.admin])


@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    return service.register(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    return service.login(session, data)


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
