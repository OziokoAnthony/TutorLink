"""Create an admin account. Admins can't self-register.

Usage:
    uv run python -m app.scripts.create_admin --email admin@tutorlink.ng
    docker compose exec app uv run python -m app.scripts.create_admin --email admin@tutorlink.ng
"""

import argparse
import getpass
import sys

from sqlmodel import Session, func, select

from app.core.security import get_password_hash
from app.db.session import engine
from app.domains.auth.models import User, UserRole


def create_admin(session: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if session.exec(select(User).where(func.lower(User.email) == email)).first():
        raise ValueError(f"A user with email {email} already exists")
    admin = User(email=email, password_hash=get_password_hash(password), role=UserRole.admin)
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a TutorLink admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="omit to be prompted (recommended)")
    args = parser.parse_args(argv)

    password = args.password
    if password is None:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm password: "):
            print("Passwords do not match", file=sys.stderr)
            return 1

    with Session(engine) as session:
        try:
            admin = create_admin(session, args.email, password)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
    print(f"Created admin {admin.email} ({admin.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
