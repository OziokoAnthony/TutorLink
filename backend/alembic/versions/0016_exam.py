"""The qualifying exam (spec 4 R5)

A bank of Claude-written multiple-choice questions, tagged general reasoning or subject + level, and
tutors' timed attempts with the questions each one showed and the answers saved before its deadline.

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

education_level = postgresql.ENUM(name="education_level", create_type=False)


def _timestamps() -> list[sa.Column]:
    return [sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)]


def upgrade() -> None:
    op.create_table(
        "exam_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("subject_key", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=True),
        sa.Column("level", education_level, nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("options", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("correct_index", sa.SmallInteger(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_exam_questions"),
        sa.UniqueConstraint("text_hash", name="uq_exam_questions_text_hash"),
    )
    op.create_index("ix_exam_questions_tag", "exam_questions", ["subject_key", "level"])

    op.create_table(
        "exam_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_exam_attempts_tutor_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_exam_attempts"),
    )
    op.create_index("ix_exam_attempts_tutor_id", "exam_attempts", ["tutor_id"])

    op.create_table(
        "exam_attempt_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("chosen_index", sa.SmallInteger(), nullable=True),
        sa.ForeignKeyConstraint(["attempt_id"], ["exam_attempts.id"],
                                name="fk_exam_attempt_questions_attempt_id_exam_attempts"),
        sa.ForeignKeyConstraint(["question_id"], ["exam_questions.id"],
                                name="fk_exam_attempt_questions_question_id_exam_questions"),
        sa.PrimaryKeyConstraint("id", name="pk_exam_attempt_questions"),
        sa.UniqueConstraint("attempt_id", "position", name="uq_exam_attempt_questions_attempt_id_position"),
    )
    op.create_index("ix_exam_attempt_questions_attempt_id", "exam_attempt_questions", ["attempt_id"])
    op.create_index("ix_exam_attempt_questions_question_id", "exam_attempt_questions", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_attempt_questions_question_id", table_name="exam_attempt_questions")
    op.drop_index("ix_exam_attempt_questions_attempt_id", table_name="exam_attempt_questions")
    op.drop_table("exam_attempt_questions")
    op.drop_index("ix_exam_attempts_tutor_id", table_name="exam_attempts")
    op.drop_table("exam_attempts")
    op.drop_index("ix_exam_questions_tag", table_name="exam_questions")
    op.drop_table("exam_questions")
