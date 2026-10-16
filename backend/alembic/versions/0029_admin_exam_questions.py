"""Admins write exam questions (spec 12): who added each question

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exam_questions", sa.Column("added_by", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_exam_questions_added_by_users", "exam_questions", "users", ["added_by"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_exam_questions_added_by_users", "exam_questions", type_="foreignkey")
    op.drop_column("exam_questions", "added_by")
