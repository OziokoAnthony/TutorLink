"""Tutor ratings: tutor_reviews (added after the original CLAUDE.md spec)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tutor_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tutor_reviews"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_tutor_reviews_tutor_id_users"),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], name="fk_tutor_reviews_parent_id_users"),
        sa.UniqueConstraint("tutor_id", "parent_id", name="uq_tutor_reviews_tutor_id_parent_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_tutor_reviews_rating_range"),
    )
    op.create_index("ix_tutor_reviews_parent_id", "tutor_reviews", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_tutor_reviews_parent_id", table_name="tutor_reviews")
    op.drop_table("tutor_reviews")
