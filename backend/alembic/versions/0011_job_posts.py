"""Job posts and applications (spec 2)

Parents post jobs, approved tutors apply, and choosing an applicant creates a booking that points
back at its job (bookings.job_id).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

education_level = postgresql.ENUM(name="education_level", create_type=False)
lesson_mode = postgresql.ENUM(name="lesson_mode", create_type=False)
billing_period = postgresql.ENUM(name="billing_period", create_type=False)
job_status = postgresql.ENUM("open", "ongoing", "completed", "closed", name="job_status", create_type=False)
application_status = postgresql.ENUM("applied", "withdrawn", "chosen", name="application_status", create_type=False)
certificate_type = postgresql.ENUM("WAEC", "NECO", "NABTEB", "NCE", "Degree", "PGDE", "TRCN", "Other",
                                   name="certificate_type", create_type=False)

NEW_ENUMS = [job_status, application_status, certificate_type]


def upgrade() -> None:
    for enum in NEW_ENUMS:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table("job_posts",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("parent_id", sa.Uuid(), nullable=False),
    sa.Column("subjects", postgresql.ARRAY(sa.String()), nullable=False),
    sa.Column("level", education_level, nullable=False),
    sa.Column("mode", lesson_mode, nullable=False),
    sa.Column("area", sa.String(), nullable=True),
    sa.Column("billing_period", billing_period, nullable=False),
    sa.Column("start_date", sa.Date(), nullable=False),
    sa.Column("end_date", sa.Date(), nullable=True),
    sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column("qualifications", sa.Text(), nullable=False),
    sa.Column("min_certificate", certificate_type, nullable=True),
    sa.Column("other_requirements", sa.Text(), nullable=True),
    sa.Column("child_strengths", sa.Text(), nullable=False),
    sa.Column("child_weaknesses", sa.Text(), nullable=False),
    sa.Column("status", job_status, server_default="open", nullable=False),
    sa.Column("booking_id", sa.Uuid(), nullable=True),
    sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(["parent_id"], ["users.id"], name=op.f("fk_job_posts_parent_id_users")),
    sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], name=op.f("fk_job_posts_booking_id_bookings")),
    sa.PrimaryKeyConstraint("id", name=op.f("pk_job_posts"))
    )
    op.create_index(op.f("ix_job_posts_parent_id"), "job_posts", ["parent_id"], unique=False)
    op.create_index("ix_job_posts_status_created_at", "job_posts", ["status", "created_at"], unique=False)

    op.create_table("job_slots",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("job_id", sa.Uuid(), nullable=False),
    sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
    sa.Column("start_time", sa.Time(), nullable=False),
    sa.Column("end_time", sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(["job_id"], ["job_posts.id"], name=op.f("fk_job_slots_job_id_job_posts")),
    sa.PrimaryKeyConstraint("id", name=op.f("pk_job_slots"))
    )
    op.create_index(op.f("ix_job_slots_job_id"), "job_slots", ["job_id"], unique=False)

    op.create_table("job_applications",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("job_id", sa.Uuid(), nullable=False),
    sa.Column("tutor_id", sa.Uuid(), nullable=False),
    sa.Column("note", sa.Text(), nullable=True),
    sa.Column("status", application_status, server_default="applied", nullable=False),
    sa.Column("withdrawn_reason", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["job_id"], ["job_posts.id"], name=op.f("fk_job_applications_job_id_job_posts")),
    sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name=op.f("fk_job_applications_tutor_id_users")),
    sa.PrimaryKeyConstraint("id", name=op.f("pk_job_applications")),
    sa.UniqueConstraint("job_id", "tutor_id", name=op.f("uq_job_applications_job_id_tutor_id"))
    )
    op.create_index(op.f("ix_job_applications_tutor_id"), "job_applications", ["tutor_id"], unique=False)

    op.add_column("bookings", sa.Column("job_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f("fk_bookings_job_id_job_posts"), "bookings", "job_posts", ["job_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(op.f("fk_bookings_job_id_job_posts"), "bookings", type_="foreignkey")
    op.drop_column("bookings", "job_id")
    op.drop_index(op.f("ix_job_applications_tutor_id"), table_name="job_applications")
    op.drop_table("job_applications")
    op.drop_index(op.f("ix_job_slots_job_id"), table_name="job_slots")
    op.drop_table("job_slots")
    op.drop_index("ix_job_posts_status_created_at", table_name="job_posts")
    op.drop_index(op.f("ix_job_posts_parent_id"), table_name="job_posts")
    op.drop_table("job_posts")
    for enum in reversed(NEW_ENUMS):
        enum.drop(op.get_bind(), checkfirst=True)
