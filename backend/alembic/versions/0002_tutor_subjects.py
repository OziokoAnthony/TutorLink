"""Step 3 (tutors): tutor_subjects

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Also used by schedules.level (0003), which must not create or drop it.
education_level = postgresql.ENUM(
    "primary", "junior_secondary", "senior_secondary", name="education_level", create_type=False
)


def upgrade() -> None:
    education_level.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "tutor_subjects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tutor_profile_id", sa.Uuid(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("level", education_level, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tutor_subjects"),
        sa.ForeignKeyConstraint(["tutor_profile_id"], ["tutor_profiles.id"],
                                name="fk_tutor_subjects_tutor_profile_id_tutor_profiles"),
        sa.UniqueConstraint("tutor_profile_id", "subject", "level",
                            name="uq_tutor_subjects_tutor_profile_id_subject_level"),
    )


def downgrade() -> None:
    op.drop_table("tutor_subjects")
    education_level.drop(op.get_bind(), checkfirst=True)
