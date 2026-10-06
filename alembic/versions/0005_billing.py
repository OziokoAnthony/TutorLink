"""Step 6 (billing): invoices, invoice_items

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

invoice_status = postgresql.ENUM("pending", "paid", "failed", name="invoice_status", create_type=False)


def upgrade() -> None:
    invoice_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=False),
        sa.Column("billing_month", sa.SmallInteger(), nullable=False),
        sa.Column("billing_year", sa.SmallInteger(), nullable=False),
        sa.Column("total_sessions", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("commission_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("paystack_reference", sa.String(), nullable=True),
        sa.Column("status", invoice_status, server_default="pending", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
        sa.ForeignKeyConstraint(["parent_id"], ["users.id"], name="fk_invoices_parent_id_users"),
        sa.UniqueConstraint("parent_id", "billing_month", "billing_year",
                            name="uq_invoices_parent_id_billing_month_billing_year"),
    )
    op.create_index("ix_invoices_paystack_reference", "invoices", ["paystack_reference"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("tutor_id", sa.Uuid(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invoice_items"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="fk_invoice_items_invoice_id_invoices"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_invoice_items_session_id_sessions"),
        sa.ForeignKeyConstraint(["tutor_id"], ["users.id"], name="fk_invoice_items_tutor_id_users"),
        sa.UniqueConstraint("session_id", name="uq_invoice_items_session_id"),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index("ix_invoices_paystack_reference", table_name="invoices")
    op.drop_table("invoices")
    invoice_status.drop(op.get_bind(), checkfirst=True)
