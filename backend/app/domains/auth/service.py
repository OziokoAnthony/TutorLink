from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import create_access_token, get_password_hash, verify_password
from app.domains.auth import photos
from app.domains.auth.models import (
    LoginRequest,
    MeResponse,
    ParentProfile,
    ParentProfileRead,
    RegisterRequest,
    TokenResponse,
    User,
    UserRead,
    UserRole,
)
from app.domains.notifications import service as notifications
from app.domains.reviews import service as review_service
from app.domains.tutors import service as tutor_service
from app.domains.tutors.models import TutorProfile


def full_names(session: Session, user_ids) -> dict[UUID, str]:
    """user id -> full_name from parent or tutor profiles, in two queries for any number of ids."""
    ids = list({uid for uid in user_ids if uid is not None})
    if not ids:
        return {}
    names = dict(session.exec(
        select(ParentProfile.user_id, ParentProfile.full_name).where(ParentProfile.user_id.in_(ids))
    ).all())
    names.update(session.exec(
        select(TutorProfile.user_id, TutorProfile.full_name).where(TutorProfile.user_id.in_(ids))
    ).all())
    return names


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(func.lower(User.email) == email.lower())).first()


def build_me(session: Session, user: User) -> MeResponse:
    me = MeResponse(user=UserRead.model_validate(user, update={"photo_url": photos.url_for(user)}))
    if user.role == UserRole.parent:
        profile = session.exec(select(ParentProfile).where(ParentProfile.user_id == user.id)).first()
        if profile:
            me.parent_profile = ParentProfileRead.model_validate(profile)
        me.tutors_to_rate = review_service.tutors_to_rate(session, user.id)
    elif user.role == UserRole.tutor:
        profile = tutor_service.get_profile_by_user_id(session, user.id)
        if profile:
            me.tutor_profile = tutor_service.build_profile_read(session, profile)
    return me


def register(session: Session, data: RegisterRequest) -> MeResponse:
    email = data.email.lower()
    if get_user_by_email(session, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=email, password_hash=get_password_hash(data.password), role=data.role)
    try:
        session.add(user)
        session.flush()  # no ORM relationships, so insert the user before its profile explicitly
        if data.role == UserRole.parent:
            session.add(ParentProfile(user_id=user.id, full_name=data.full_name, phone=data.phone,
                                      address=data.address))
        else:
            session.add(TutorProfile(user_id=user.id, full_name=data.full_name, phone=data.phone,
                                     bio=data.bio, area=data.area))
            for offer in data.offers:
                tutor_service.add_offer_rows(session, user.id, offer)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        if getattr(exc.orig.diag, "constraint_name", None) == "uq_users_email":  # lost a registration race
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        raise

    session.refresh(user)
    if user.role == UserRole.tutor:
        notifications.tutor_application_received(user.email, data.full_name)
    return build_me(session, user)


def login(session: Session, data: LoginRequest) -> TokenResponse:
    user = get_user_by_email(session, data.email)
    if user is None or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))


def remove_photo(session: Session, user_id: UUID) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    photos.remove_photo(session, user)
    notifications.notify(session, user.id, "Please upload a new profile picture",
                         "Your profile picture was removed by TutorLink. Please upload a new one.",
                         "/dashboard")
    session.commit()
