"""One super admin, who adds and removes the other admins and can't be removed

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_super_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("uq_users_one_super_admin", "users", ["is_super_admin"], unique=True,
                    postgresql_where=sa.text("is_super_admin"))
    # On a database that already has admins, the oldest active one becomes the super admin.
    op.execute("""
        UPDATE users SET is_super_admin = true WHERE id = (
            SELECT id FROM users WHERE role = 'admin' AND is_active ORDER BY created_at LIMIT 1)
    """)


def downgrade() -> None:
    op.drop_index("uq_users_one_super_admin", table_name="users")
    op.drop_column("users", "is_super_admin")
