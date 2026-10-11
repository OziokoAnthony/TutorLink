"""Tutor certificates (spec 4 R4)

Each certificate's file is private in storage. WAEC/NECO results carry an exam number, exam year and an
encrypted result-checker PIN, erased once an admin reviews the certificate. The certificate types
are the `certificate_type` enum job posts already use for their minimum certificate.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

certificate_type = postgresql.ENUM(name="certificate_type", create_type=False)  # from 0011 (job posts)
certificate_status = postgresql.ENUM("pending", "verified", "rejected", name="certificate_status", create_type=False)


def upgrade() -> None:
    certificate_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("type", certificate_type, nullable=False),
        sa.Column("institution", sa.String(), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column("file_key", sa.String(), nullable=False),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("exam_number", sa.String(), nullable=True),
        sa.Column("exam_year", sa.SmallInteger(), nullable=True),
        sa.Column("checker_pin_encrypted", sa.String(), nullable=True),
        sa.Column("status", certificate_status, server_default="pending", nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_certificates_tutor_id_users"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name="fk_certificates_reviewed_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_certificates"),
    )
    op.create_index("ix_certificates_tutor_id", "certificates", ["tutor_id"])


def downgrade() -> None:
    op.drop_index("ix_certificates_tutor_id", table_name="certificates")
    op.drop_table("certificates")
    certificate_status.drop(op.get_bind(), checkfirst=True)
