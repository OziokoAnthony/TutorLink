"""Tutor work emails and separate first name / surname

Tutors get a work email (initial of surname + "." + first name @ TUTOR_EMAIL_DOMAIN) that is their
only login. Existing tutors' full_name is split (first word / last word) and each gets an address.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-07
"""
import unicodedata
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _letters(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in folded.lower() if "a" <= c <= "z")


def upgrade() -> None:
    op.add_column("users", sa.Column("work_email", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_work_email", "users", ["work_email"])
    op.add_column("tutor_profiles", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("tutor_profiles", sa.Column("surname", sa.String(), nullable=True))

    conn = op.get_bind()
    domain = "tutorlink.com"  # the setting was removed with work emails (0019)
    taken: set[str] = set()
    rows = conn.execute(sa.text("SELECT id, user_id, full_name FROM tutor_profiles ORDER BY created_at")).all()
    for profile_id, user_id, full_name in rows:
        words = full_name.split() or ["Tutor"]
        first, surname = words[0], words[-1] if len(words) > 1 else words[0]
        base = f"{_letters(surname)[:1] or 't'}.{_letters(first) or 'tutor'}"
        n = 1
        while (email := f"{base}{n if n > 1 else ''}@{domain}") in taken:
            n += 1
        taken.add(email)
        conn.execute(sa.text("UPDATE tutor_profiles SET first_name = :f, surname = :s WHERE id = :id"),
                     {"f": first, "s": surname, "id": profile_id})
        conn.execute(sa.text("UPDATE users SET work_email = :e WHERE id = :id"), {"e": email, "id": user_id})

    op.alter_column("tutor_profiles", "first_name", nullable=False)
    op.alter_column("tutor_profiles", "surname", nullable=False)


def downgrade() -> None:
    op.drop_column("tutor_profiles", "surname")
    op.drop_column("tutor_profiles", "first_name")
    op.drop_constraint("uq_users_work_email", "users", type_="unique")
    op.drop_column("users", "work_email")
