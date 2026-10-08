"""Tutor onboarding: NIN verification with Dojah (spec 4 R2, R3)

Tutors give a middle name when their NIN record has one, and their name locks once the NIN is
verified. Each NIN check is recorded without the full NIN: last 4 digits and a keyed hash, which may
be verified on only one account.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tutor_profiles", sa.Column("middle_name", sa.String(), nullable=True))
    op.add_column("tutor_profiles", sa.Column("nin_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "nin_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("nin_last4", sa.String(), nullable=False),
        sa.Column("nin_hash", sa.String(), nullable=False),
        sa.Column("nin_found", sa.Boolean(), nullable=False),
        sa.Column("name_matches", sa.Boolean(), nullable=True),
        sa.Column("selfie_matches", sa.Boolean(), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("dojah_reference", sa.String(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_nin_verifications_tutor_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_nin_verifications"),
    )
    op.create_index("ix_nin_verifications_tutor_id", "nin_verifications", ["tutor_id"])
    op.create_index("ix_nin_verifications_nin_hash", "nin_verifications", ["nin_hash"])
    op.create_index("uq_nin_verifications_verified_nin_hash", "nin_verifications", ["nin_hash"], unique=True,
                    postgresql_where=sa.text("verified"))


def downgrade() -> None:
    op.drop_index("uq_nin_verifications_verified_nin_hash", table_name="nin_verifications")
    op.drop_index("ix_nin_verifications_nin_hash", table_name="nin_verifications")
    op.drop_index("ix_nin_verifications_tutor_id", table_name="nin_verifications")
    op.drop_table("nin_verifications")
    op.drop_column("tutor_profiles", "nin_verified_at")
    op.drop_column("tutor_profiles", "middle_name")
