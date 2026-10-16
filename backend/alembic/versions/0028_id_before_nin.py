"""ID documents before the NIN, and NIN-deadline reminders (spec 11)

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

id_document_type = postgresql.ENUM("nin", "voters_card", "drivers_licence", "passport", name="id_document_type",
                                   create_type=False)
id_document_status = postgresql.ENUM("pending", "verified", "rejected", name="id_document_status", create_type=False)


def upgrade() -> None:
    id_document_type.create(op.get_bind(), checkfirst=True)
    id_document_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "id_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("type", id_document_type, nullable=False),
        sa.Column("file_key", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("status", id_document_status, nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_id_documents_tutor_id_users"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_id_documents_reviewed_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_id_documents"),
    )
    op.create_index("ix_id_documents_tutor_id", "id_documents", ["tutor_id"])
    op.add_column("tutor_profiles", sa.Column("nin_reminder_days", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("tutor_profiles", "nin_reminder_days")
    op.drop_index("ix_id_documents_tutor_id", table_name="id_documents")
    op.drop_table("id_documents")
    id_document_status.drop(op.get_bind(), checkfirst=True)
    id_document_type.drop(op.get_bind(), checkfirst=True)
