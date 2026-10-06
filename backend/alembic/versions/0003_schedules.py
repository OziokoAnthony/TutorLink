"""Step 4 (schedules): schedules

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Created in 0002 (tutor_subjects); reused here.
education_level = postgresql.ENUM(
    "primary", "junior_secondary", "senior_secondary", name="education_level", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("level", education_level, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_schedules"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_schedules_tutor_id_users"),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], name="fk_schedules_parent_id_users"),
    )
    op.create_index("ix_schedules_tutor_id_day_of_week_is_active", "schedules",
                    ["tutor_id", "day_of_week", "is_active"])
    op.create_index("ix_schedules_parent_id", "schedules", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_schedules_parent_id", table_name="schedules")
    op.drop_index("ix_schedules_tutor_id_day_of_week_is_active", table_name="schedules")
    op.drop_table("schedules")
