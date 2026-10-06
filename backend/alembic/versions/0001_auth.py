"""Step 2 (auth): users, parent_profiles, tutor_profiles

Revision ID: 0001
Revises:
Create Date: 2026-10-06

tutor_profiles is created here because registering as a tutor creates the profile.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("parent", "tutor", "admin", name="user_role", create_type=False)
vetting_status = postgresql.ENUM("pending", "approved", "rejected", name="vetting_status", create_type=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    vetting_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_table(
        "parent_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_parent_profiles"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_parent_profiles_user_id_users"),
        sa.UniqueConstraint("user_id", name="uq_parent_profiles_user_id"),
    )
    op.create_table(
        "tutor_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("area", sa.String(), nullable=False),
        sa.Column("rate_per_session", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("vetting_status", vetting_status, server_default="pending", nullable=False),
        sa.Column("vetting_note", sa.Text(), nullable=True),
        sa.Column("vetted_by", sa.Uuid(), nullable=True),
        sa.Column("vetted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_tutor_profiles"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_tutor_profiles_user_id_users"),
        sa.ForeignKeyConstraint(["vetted_by"], ["users.id"], name="fk_tutor_profiles_vetted_by_users"),
        sa.UniqueConstraint("user_id", name="uq_tutor_profiles_user_id"),
    )


def downgrade() -> None:
    op.drop_table("tutor_profiles")
    op.drop_table("parent_profiles")
    op.drop_table("users")
    bind = op.get_bind()
    vetting_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
