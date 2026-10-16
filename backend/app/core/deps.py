from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.config import settings
from app.core.security import decode_access_token, token_lifetime
from app.db.session import get_session
from app.domains.auth.models import User, UserRole
from app.domains.content import service as content
from app.domains.users import service as people

# auto_error=False so a missing token is a 401 (not FastAPI's default 403).
bearer_scheme = HTTPBearer(auto_error=False)

# The browser keeps the login token in this httpOnly cookie, which page scripts can't read, so a script
# injected into a page can't steal it. API clients and tests can send it as a Bearer header instead.
SESSION_COOKIE = "tutorlink_token"
# Requests that change something and are authenticated by the cookie must carry this header. Browsers only
# let another site send a custom header after a CORS check, which only FRONTEND_URL passes, so a hostile
# page can't make a logged-in visitor's browser act for them (CSRF).
CSRF_HEADER, CSRF_VALUE = "X-Requested-With", "TutorLink"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def set_session_cookie(response: Response, token: str, role: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=int(token_lifetime(role).total_seconds()), httponly=True,
        secure=settings.BASE_URL.startswith("https://"), samesite="lax",
        domain=settings.COOKIE_DOMAIN or None, path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, domain=settings.COOKIE_DOMAIN or None, path="/")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_session),
) -> User:
    if credentials is not None:
        token = credentials.credentials
    else:
        token = request.cookies.get(SESSION_COOKIE)
        if token is None:
            raise _unauthorized()
        if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This request didn't come from the TutorLink site")
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _unauthorized("Invalid or expired token")

    user = session.get(User, user_id)
    if user is None or not user.is_active or payload.get("ver", 0) != user.token_version:
        raise _unauthorized("Invalid or expired token")
    people.touch(session, user)  # last seen (spec 10 R1)
    _check_agreement(request, session, user)
    return user


# What a parent or tutor who must agree to the latest legal documents can still do (spec 9 R3.2): read their
# account and notifications, read and agree to the documents, and log out.
ALLOWED_BEFORE_AGREEING = {
    ("GET", "/v1/auth/me"), ("POST", "/v1/auth/logout"), ("GET", "/v1/notifications/me"),
    ("GET", "/v1/legal/me"), ("POST", "/v1/legal/me/accept"),
}
MUST_AGREE = "Please read and agree to TutorLink's terms to continue."


def _check_agreement(request: Request, session: Session, user: User) -> None:
    if user.role == UserRole.admin or (request.method, request.url.path) in ALLOWED_BEFORE_AGREEING:
        return
    if content.must_agree_now(session, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, MUST_AGREE)


def require_roles(roles: list[UserRole]):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user

    return checker


# Tutors' profiles, schedules and reviews are for registered parents (and admins), not anonymous visitors.
can_see_tutors = require_roles([UserRole.parent, UserRole.admin])
