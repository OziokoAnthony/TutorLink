from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.core.deps import get_current_user
from app.db.session import get_session
from app.domains.auth import service
from app.domains.auth.models import LoginRequest, MeResponse, RegisterRequest, TokenResponse, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, session: Session = Depends(get_session)):
    return service.register(session, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    return service.login(session, data)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return service.build_me(session, user)
