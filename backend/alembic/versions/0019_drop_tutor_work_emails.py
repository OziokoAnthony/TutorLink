"""Tutors no longer get a TutorLink work email (spec 4 R0, R1, changed 2026-10-09)

Everyone signs up and logs in with their own email, with a password or Google. Tutors who had a work email
log in with their own email (users.email) and the same password from now on.

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_users_work_email", "users", type_="unique")
    op.drop_column("users", "work_email")


def downgrade() -> None:
    """The column comes back empty: the old addresses aren't kept."""
    op.add_column("users", sa.Column("work_email", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_work_email", "users", ["work_email"])
