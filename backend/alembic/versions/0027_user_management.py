"""Last seen, removal notices and removed accounts (spec 10)

Accounts that are already deactivated (is_active false) count as removed from now on.

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("last_seen_at", "removal_noticed_at", "removal_due_at", "removed_at")


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column("users", sa.Column(name, sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("removal_reason", sa.Text(), nullable=True))
    op.execute("UPDATE users SET removed_at = updated_at WHERE NOT is_active AND role <> 'admin'")


def downgrade() -> None:
    op.drop_column("users", "removal_reason")
    for name in reversed(COLUMNS):
        op.drop_column("users", name)
