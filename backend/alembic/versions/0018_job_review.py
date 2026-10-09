"""Job posts are reviewed by an admin before tutors see them (spec 2 R1.4)

New and edited jobs start `pending`; an admin opens or rejects them. Jobs already open stay open.

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New enum values can't be used in the transaction that adds them, so they're committed first.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'pending'")
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'rejected'")
    op.alter_column("job_posts", "status", server_default="pending")
    op.add_column("job_posts", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column("job_posts", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """PostgreSQL can't drop enum values, so the type is rebuilt. Jobs still waiting for review or
    rejected are closed, the nearest old status."""
    op.drop_column("job_posts", "reviewed_at")
    op.drop_column("job_posts", "review_note")
    op.alter_column("job_posts", "status", server_default=None)
    op.execute("UPDATE job_posts SET status = 'closed' WHERE status IN ('pending', 'rejected')")
    op.execute("ALTER TYPE job_status RENAME TO job_status_old")
    op.execute("CREATE TYPE job_status AS ENUM ('open', 'ongoing', 'completed', 'closed')")
    op.execute("ALTER TABLE job_posts ALTER COLUMN status TYPE job_status USING status::text::job_status")
    op.execute("DROP TYPE job_status_old")
    op.alter_column("job_posts", "status", server_default="open")
