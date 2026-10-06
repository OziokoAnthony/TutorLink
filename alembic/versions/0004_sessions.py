"""Step 5 (sessions): sessions

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

session_status = postgresql.ENUM(
    "scheduled", "logged", "confirmed", "cancelled", name="session_status", create_type=False
)


def upgrade() -> None:
    session_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("topic_covered", sa.Text(), nullable=True),
        sa.Column("homework", sa.Text(), nullable=True),
        sa.Column("status", session_status, server_default="scheduled", nullable=False),
        sa.Column("logged_by", sa.Uuid(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], name="fk_sessions_schedule_id_schedules"),
        sa.ForeignKeyConstraint(["logged_by"], ["users.id"], name="fk_sessions_logged_by_users"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], name="fk_sessions_confirmed_by_users"),
        sa.UniqueConstraint("schedule_id", "session_date", name="uq_sessions_schedule_id_session_date"),
    )


def downgrade() -> None:
    op.drop_table("sessions")
    session_status.drop(op.get_bind(), checkfirst=True)
