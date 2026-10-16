"""Nursery and exam-prep levels, the guardian confirmation, and how people heard about TutorLink (spec 15)

PostgreSQL can't drop an enum value, so the downgrade keeps the two levels; the upgrade adds them only if missing.

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE education_level ADD VALUE IF NOT EXISTS 'nursery' BEFORE 'primary'")
    op.execute("ALTER TYPE education_level ADD VALUE IF NOT EXISTS 'exam_prep' AFTER 'international'")
    for table in ("bookings", "job_posts"):
        op.add_column(table, sa.Column("guardian_confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("heard_from", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "heard_from")
    for table in ("bookings", "job_posts"):
        op.drop_column(table, "guardian_confirmed_at")
