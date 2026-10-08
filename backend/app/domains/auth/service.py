from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core import clock, google
from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_password,
    generate_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.domains.auth import photos, work_email
from app.domains.auth.models import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    GoogleRegisterRequest,
    GoogleRegisterResponse,
    LoginRequest,
    MeResponse,
    ParentProfile,
    ParentProfileRead,
    PasswordResetToken,
    ProfileFields,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    User,
    UserRead,
    UserRole,
)
from app.domains.notifications import service as notifications
from app.domains.reviews import service as review_service
from app.domains.tutors import service as tutor_service
from app.domains.tutors.models import TutorProfile

RESET_LINK_LIFETIME = timedelta(hours=1)  # R0.7


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


def get_user_by_work_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(func.lower(User.work_email) == email.lower())).first()


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


def _check_new_email(session: Session, email: str) -> None:
    if work_email.is_work_domain(email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Please register with your own email. TutorLink email addresses are given to tutors after they register.")
    if get_user_by_email(session, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")


def _create_account(session: Session, data: ProfileFields, email: str, password: str | None) -> User:
    """Creates the user and their parent or tutor profile. Tutors are assigned a work email (R0.2)."""
    user = User(email=email, password_hash=get_password_hash(password) if password else None, role=data.role)
    if data.role == UserRole.tutor:
        user.work_email = work_email.next_work_email(session, data.first_name, data.surname)
    try:
        session.add(user)
        session.flush()  # no ORM relationships, so insert the user before its profile explicitly
        if data.role == UserRole.parent:
            session.add(ParentProfile(user_id=user.id, full_name=data.full_name, phone=data.phone,
                                      address=data.address))
        else:
            session.add(TutorProfile(user_id=user.id, first_name=data.first_name, middle_name=data.middle_name,
                                     surname=data.surname,
                                     full_name=data.full_name, phone=data.phone, bio=data.bio, area=data.area))
            for offer in data.offers:
                tutor_service.add_offer_rows(session, user.id, offer)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        constraint = getattr(exc.orig.diag, "constraint_name", None)
        if constraint == "uq_users_email":  # lost a registration race
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        if constraint == "uq_users_work_email":  # another tutor with the same name registered at the same moment
            raise HTTPException(status.HTTP_409_CONFLICT, "Something went wrong creating your account. Please try again.")
        raise
    session.refresh(user)
    return user


def register(session: Session, data: RegisterRequest) -> MeResponse:
    """Email and password sign-up, for parents. Tutors register with Google (spec 4 R1.1)."""
    email = data.email.lower()
    _check_new_email(session, email)
    user = _create_account(session, data, email, data.password)
    return build_me(session, user)


def google_register(session: Session, data: GoogleRegisterRequest) -> GoogleRegisterResponse:
    """Sign-up with Google (spec 4 R1). The verified Google email becomes the personal email. Tutors are
    given a work email and a generated password, shown once and emailed (R1.2); parents are signed in
    and have no password until they set one with "Forgot password?" (R1.4)."""
    identity = google.verify_id_token(data.id_token)
    existing = get_user_by_email(session, identity.email)
    if existing is not None:
        if existing.role != data.role:  # R1.6
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"This Google account is already registered as a {existing.role.value} on TutorLink")
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an account. Please log in.")
    _check_new_email(session, identity.email)

    password = generate_password() if data.role == UserRole.tutor else None
    user = _create_account(session, data, identity.email, password)
    if data.use_google_photo and (picture := google.fetch_photo(identity.picture)):
        try:
            photos.set_photo(session, user, picture)
        except HTTPException:  # not an image we accept: they upload one themselves
            pass

    response = GoogleRegisterResponse(**build_me(session, user).model_dump())
    if user.role == UserRole.tutor:
        notifications.tutor_application_received(user.email, data.full_name, user.work_email, password)
        response.password = password
    else:
        response.access_token = create_access_token(str(user.id), user.role.value)
    return response


def google_login(session: Session, data: GoogleLoginRequest) -> TokenResponse:
    """Parents only (R1.4). Tutors log in with their work email (R1.3), admins with their password (R1.7).
    These messages come only after Google verified the token, so they tell a stranger nothing."""
    identity = google.verify_id_token(data.id_token)
    user = get_user_by_email(session, identity.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "There's no TutorLink account for this Google email yet. Sign up to create one.")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account has been deactivated")
    if user.role == UserRole.tutor:
        login_with = f"your TutorLink email: {user.work_email}" if user.work_email else "your email and password"
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Tutors can't log in with Google. Log in with {login_with}")
    if user.role == UserRole.admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admins log in with their email and password")
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))


def login(session: Session, data: LoginRequest) -> TokenResponse:
    """Tutors log in with their work email only; parents and admins with their own email."""
    user = get_user_by_work_email(session, data.email) or get_user_by_email(session, data.email)
    if user is None or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.work_email and user.work_email != data.email.lower():
        # Right password, personal email: point them to their work email (checked after the password,
        # so it tells a stranger nothing).
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Tutors log in with their TutorLink email: {user.work_email}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))


def change_password(session: Session, user: User, data: ChangePasswordRequest) -> None:
    if user.password_hash is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "You signed up with Google and have no password yet. "
                            "Set one with \"Forgot password?\" on the login page.")
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Your current password is incorrect")
    user.password_hash = get_password_hash(data.new_password)
    session.add(user)
    session.commit()


def forgot_password(session: Session, data: ForgotPasswordRequest) -> tuple[str, str, str] | None:
    """Spec 4 R0.7. Makes a one-hour, single-use reset link for the account with this personal email and
    returns the email to send (to, subject, html), or None. The caller answers the same either way."""
    user = get_user_by_email(session, data.email)
    if user is None or not user.is_active or user.role == UserRole.admin:
        return None
    token = generate_token()
    session.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(token),
                                   expires_at=clock.now() + RESET_LINK_LIFETIME))
    session.commit()
    name = full_names(session, [user.id]).get(user.id, "there")
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    return user.email, *notifications.password_reset_email(name, link, user.work_email)


def reset_password(session: Session, data: ResetPasswordRequest) -> None:
    """Sets a new password from a reset link (R0.7). Other devices stay logged in; the old password stops working."""
    reset = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(data.token)).with_for_update()
    ).first()
    user = session.get(User, reset.user_id) if reset else None
    if reset is None or reset.used_at is not None or reset.expires_at <= clock.now() or not user.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "This link has expired or was already used. Ask for a new one with \"Forgot password?\".")
    user.password_hash = get_password_hash(data.new_password)
    session.add(user)
    # The link works once, and any older links stop working too.
    for pending in session.exec(select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))).all():
        pending.used_at = clock.now()
        session.add(pending)
    session.commit()


def remove_photo(session: Session, user_id: UUID) -> None:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    photos.remove_photo(session, user)
    notifications.notify(session, user.id, "Please upload a new profile picture",
                         "Your profile picture was removed by TutorLink. Please upload a new one.",
                         "/dashboard")
    session.commit()
