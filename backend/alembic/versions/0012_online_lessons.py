"""Online lessons: meeting links, recording consent and lesson recordings (spec 3)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bookings", sa.Column("meeting_link", sa.String(), nullable=True))
    op.add_column("bookings", sa.Column("recording_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bookings", sa.Column("recording_consent_text", sa.Text(), nullable=True))
    op.add_column("job_posts", sa.Column("recording_consent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_posts", sa.Column("recording_consent_text", sa.Text(), nullable=True))
    op.add_column("lessons", sa.Column("recording_key", sa.String(), nullable=True))
    op.add_column("lessons", sa.Column("recording_content_type", sa.String(), nullable=True))
    op.add_column("lessons", sa.Column("recording_size", sa.BigInteger(), nullable=True))
    op.add_column("lessons", sa.Column("recording_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lessons", sa.Column("recording_deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in ("recording_deleted_at", "recording_uploaded_at", "recording_size", "recording_content_type",
                   "recording_key"):
        op.drop_column("lessons", column)
    op.drop_column("job_posts", "recording_consent_text")
    op.drop_column("job_posts", "recording_consent_at")
    op.drop_column("bookings", "recording_consent_text")
    op.drop_column("bookings", "recording_consent_at")
    op.drop_column("bookings", "meeting_link")
