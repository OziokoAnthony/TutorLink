"""Feedback from parents and tutors, answered by admins (spec 6)

Help-chat conversations sent to the team are kept with the feedback, as JSON.

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

feedback_kind = postgresql.ENUM("problem", "suggestion", "praise", "question", name="feedback_kind", create_type=False)


def upgrade() -> None:
    feedback_kind.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", feedback_kind, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("transcript", postgresql.JSONB(), nullable=True),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_feedback_user_id_users"),
        sa.ForeignKeyConstraint(["replied_by"], ["users.id"], name="fk_feedback_replied_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_feedback"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
    feedback_kind.drop(op.get_bind(), checkfirst=True)
