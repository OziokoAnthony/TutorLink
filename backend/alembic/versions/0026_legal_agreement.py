"""Parents and tutors get their own legal documents and agree to them (spec 9)

Every existing version of the privacy notice, terms and disclaimer becomes the parents' version, and is copied for
tutors with the same date, so both start with today's text (R1.1).

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

legal_audience = postgresql.ENUM("parent", "tutor", name="legal_audience", create_type=False)


def upgrade() -> None:
    legal_audience.create(op.get_bind(), checkfirst=True)
    op.add_column("legal_documents", sa.Column("audience", legal_audience, server_default="parent", nullable=False))
    op.execute("""
        INSERT INTO legal_documents (id, created_at, updated_at, audience, kind, body, published_by)
        SELECT gen_random_uuid(), created_at, updated_at, 'tutor', kind, body, published_by
        FROM legal_documents WHERE audience = 'parent'
    """)
    op.alter_column("legal_documents", "audience", server_default=None)
    op.drop_index("ix_legal_documents_kind", table_name="legal_documents")
    op.create_index("ix_legal_documents_audience_kind_created_at", "legal_documents",
                    ["audience", "kind", "created_at"])

    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_legal_acceptances_user_id_users"),
        sa.ForeignKeyConstraint(["document_id"], ["legal_documents.id"],
                                name="fk_legal_acceptances_document_id_legal_documents"),
        sa.PrimaryKeyConstraint("id", name="pk_legal_acceptances"),
        sa.UniqueConstraint("user_id", "document_id", name="uq_legal_acceptances_user_document"),
    )
    op.create_index("ix_legal_acceptances_user_id", "legal_acceptances", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_legal_acceptances_user_id", table_name="legal_acceptances")
    op.drop_table("legal_acceptances")
    op.execute("DELETE FROM legal_documents WHERE audience = 'tutor'")
    op.drop_index("ix_legal_documents_audience_kind_created_at", table_name="legal_documents")
    op.create_index("ix_legal_documents_kind", "legal_documents", ["kind"])
    op.drop_column("legal_documents", "audience")
    legal_audience.drop(op.get_bind(), checkfirst=True)
