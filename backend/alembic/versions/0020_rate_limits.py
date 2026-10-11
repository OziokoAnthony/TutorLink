"""Rate limits on login, sign-up and password reset

Each counted attempt is a row; the background jobs delete rows older than a day.

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_rate_limit_hits"),
    )
    op.create_index("ix_rate_limit_hits_key_created_at", "rate_limit_hits", ["key", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_hits_key_created_at", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
