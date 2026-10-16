"""Admin names and the admin activity log (spec 8)

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(), nullable=True))
    op.create_table(
        "admin_activity",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("admin_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_admin_activity_admin_id_created_at", "admin_activity", ["admin_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_activity_admin_id_created_at", table_name="admin_activity")
    op.drop_table("admin_activity")
    op.drop_column("users", "name")
